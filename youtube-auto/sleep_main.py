"""Spiritus Sleep & Ambient Bible Meditation independent long-form pipeline (1-2 Hours)."""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from config import (
    CHANNEL_NAME,
    MUSIC_DIR,
    OUTPUT_DIR,
    SLEEP_FPS,
    SLEEP_HEIGHT,
    SLEEP_MUSIC_VOLUME,
    SLEEP_PUBLISH_HOUR,
    SLEEP_PUBLISH_TIMEZONE,
    SLEEP_PUBLISH_WEEKDAYS,
    SLEEP_TARGET_DURATION,
    SLEEP_TTS_PITCH,
    SLEEP_TTS_RATE,
    SLEEP_VOICE,
    SLEEP_WIDTH,
    TARGET_RELIGION,
    YOUTUBE_CATEGORY,
    YOUTUBE_LANGUAGE,
)
from modules.cloudflare_image_gen import generate_single_image
from modules.sleep_script_gen import (
    SLEEP_TOPICS,
    generate_sleep_script,
    load_sleep_history,
    record_sleep_topic,
    select_sleep_topic,
)
from modules.sleep_video_maker import (
    build_final_sleep_video,
    build_sleep_base_video,
    prepare_sleep_audio,
)
from modules.thumbnail_maker import create_thumbnail
from modules.tts import text_to_speech
from modules.uploader import authenticate_youtube, schedule_video, upload_captions, upload_video

BASE_DIR = Path(__file__).parent
SLEEP_ROOT = OUTPUT_DIR / "sleep"
SLEEP_HISTORY = BASE_DIR / ".sleep_topic_history.txt"
SLEEP_LOG_DIR = BASE_DIR / "logs" / "sleep"
SLEEP_LOG_DIR.mkdir(parents=True, exist_ok=True)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

log_path = SLEEP_LOG_DIR / f"sleep_pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")],
)
logger = logging.getLogger("sleep_pipeline")


def _run_id() -> str:
    return f"sleep_{datetime.now():%Y%m%d_%H%M%S}"


def next_sleep_publish_time(now: datetime | None = None) -> datetime:
    eastern = ZoneInfo(SLEEP_PUBLISH_TIMEZONE)
    current = now.astimezone(eastern) if now else datetime.now(eastern)
    candidates = []
    for offset in range(8):
        day = current + timedelta(days=offset)
        if day.weekday() in set(SLEEP_PUBLISH_WEEKDAYS):
            candidate = day.replace(hour=SLEEP_PUBLISH_HOUR, minute=0, second=0, microsecond=0)
            if candidate > current:
                candidates.append(candidate)
    if not candidates:
        raise RuntimeError("Could not calculate next sleep publish time")
    return min(candidates)


def _music() -> str | None:
    files = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.wav"))
    return str(files[datetime.now().toordinal() % len(files)]) if files else None


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_placeholder_dark_image(path: Path, prompt_text: str, width: int = 1344, height: int = 768) -> None:
    """Generate a clean dark-mode placeholder oil painting aesthetic if AI provider is unreachable in dry-run."""
    img = Image.new("RGB", (width, height), color=(18, 22, 32))
    draw = ImageDraw.Draw(img)
    # Draw subtle night atmospheric gradient / candle glow
    for r in range(160, 0, -4):
        alpha_color = (int(30 + (160 - r) * 0.8), int(25 + (160 - r) * 0.5), int(15 + (160 - r) * 0.2))
        draw.ellipse([width // 2 - r * 3, height // 2 - r * 2, width // 2 + r * 3, height // 2 + r * 2], fill=alpha_color)
    draw.text((width // 2 - 200, height // 2), "Spiritus Night Meditation Visual", fill=(180, 170, 150))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=90)


def generate_sleep_images(prompts: list[str], output_dir: Path, run_id: str, dry_run: bool = False) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[str] = []
    for i, prompt in enumerate(prompts, 1):
        target = output_dir / f"{run_id}_visual_{i:02d}.jpg"
        if target.exists() and target.stat().st_size > 5000:
            image_paths.append(str(target))
            continue
        try:
            logger.info("Generating sleep image %d/%d: %s", i, len(prompts), prompt[:60])
            generate_single_image(prompt, target, width=1344, height=768, seed=secrets.randbelow(2_147_483_647) + 1)
        except Exception as e:
            if dry_run:
                logger.warning("Dry-run fallback for image generation: %s", e)
                _generate_placeholder_dark_image(target, prompt)
            else:
                raise e
        image_paths.append(str(target))
        if i < len(prompts):
            time.sleep(1.0)
    return image_paths


def build_sleep_description(script: dict, duration_seconds: int) -> str:
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    dur_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    chapters = [
        "00:00 Opening & Deep Breath Relaxation",
        "04:30 Holy Scripture Meditation",
        "28:00 Bedtime Prayer of Surrender & Protection",
        "36:00 Benediction & Deep Sleep Ambient Rain",
    ]

    return (
        f"{script.get('title')}\n\n"
        f"{script.get('summary', '').strip()}\n\n"
        f"Length: {dur_str} | Continuous peace and anxiety relief for nighttime rest.\n\n"
        f"Chapters:\n" + "\n".join(chapters) + "\n\n"
        f"Scripture Passage: {script.get('passage', 'Holy Bible')}\n\n"
        "How to use this video:\n"
        "1. Dim your bedroom lights and set your phone volume to a comfortable, low level.\n"
        "2. Take slow, deep breaths as the prayer begins.\n"
        "3. Release all overthinking and worries into God's caring hands.\n"
        "4. Let the peaceful rain and ambient melody carry you into deep, restorative sleep.\n\n"
        "God bless you and keep you tonight.\n\n"
        "#BibleSleep #NightPrayer #Psalm91 #ChristianMeditation #PeaceInGod #FallAsleepFast"
    )[:5000]


def run_sleep_pipeline(
    upload: bool = True,
    dry_run: bool = False,
    topic_id: str | None = None,
    duration: int | None = None,
    now: datetime | None = None,
) -> dict:
    started = time.time()
    run_id = _run_id()
    target_duration = duration or SLEEP_TARGET_DURATION
    run_root = SLEEP_ROOT / run_id
    for name in ("scripts", "audio", "images", "thumbnails", "videos"):
        (run_root / name).mkdir(parents=True, exist_ok=True)

    result = {
        "success": False,
        "run_id": run_id,
        "topic_id": None,
        "video_path": None,
        "youtube_id": None,
        "duration_seconds": target_duration,
        "errors": [],
    }
    logger.info("Spiritus Sleep pipeline started: %s (Target Duration: %ds)", run_id, target_duration)

    try:
        if upload and not dry_run:
            authenticate_youtube()

        selected_id, topic = select_sleep_topic(SLEEP_HISTORY, topic_id)
        result["topic_id"] = selected_id
        logger.info("Selected Sleep Topic: %s (%s)", selected_id, topic["bible_passage"])

        # 1. Script generation
        script = generate_sleep_script(topic)
        _write_json(run_root / "scripts" / "script.json", script)
        logger.info("Script created: %s", script["title"])

        # 2. TTS Voice generation
        raw_voice_path = run_root / "audio" / "voice_narration.mp3"
        text_to_speech(
            script["narration"],
            raw_voice_path,
            voice=SLEEP_VOICE,
            rate=SLEEP_TTS_RATE,
            pitch=SLEEP_TTS_PITCH,
        )
        srt_path = raw_voice_path.with_suffix(".srt")

        # 3. Ambient Audio Mixing (Full Target Duration)
        full_audio_path = run_root / "audio" / "final_sleep_audio.m4a"
        prepare_sleep_audio(
            voice_path=raw_voice_path,
            music_path=_music(),
            output_path=full_audio_path,
            target_duration_sec=target_duration,
            music_volume=SLEEP_MUSIC_VOLUME,
        )

        # 4. Image Generation (4-6 dark atmospheric images)
        prompts = script.get("visual_prompts", [])[:6]
        image_paths = generate_sleep_images(prompts, run_root / "images", run_id, dry_run=dry_run)

        # 5. Thumbnail Generation
        thumb_path = run_root / "thumbnails" / f"{run_id}_thumb.jpg"
        create_thumbnail(
            image_path=image_paths[0],
            title=script.get("thumbnail_text", "SLEEP IN PEACE"),
            religion=TARGET_RELIGION,
            output_path=thumb_path,
            subtitle="2 HOURS CALM SCRIPTURE",
        )

        # 6. Video Generation (2-3 min loop + stream-copy muxing)
        base_video_path = run_root / "videos" / "base_loop.mp4"
        build_sleep_base_video(
            image_paths=image_paths,
            output_path=base_video_path,
            width=SLEEP_WIDTH,
            height=SLEEP_HEIGHT,
            fps=SLEEP_FPS,
            display_per_image=35.0,
            crossfade=3.0,
        )

        final_video_path = run_root / "videos" / f"{run_id}.mp4"
        build_final_sleep_video(
            base_video_path=base_video_path,
            audio_path=full_audio_path,
            output_path=final_video_path,
        )
        result["video_path"] = str(final_video_path)

        # 7. Upload & Scheduling
        publish_at = next_sleep_publish_time(now)
        result["publish_at"] = publish_at.isoformat()

        if upload and not dry_run:
            youtube_id = upload_video(
                video_path=str(final_video_path),
                thumbnail_path=str(thumb_path),
                title=script["title"][:100],
                description=build_sleep_description(script, target_duration),
                tags=list(script.get("tags", []))[:15],
                category_id=YOUTUBE_CATEGORY,
                language=YOUTUBE_LANGUAGE,
                privacy="private",
                publish_at=None,
                made_for_kids=False,
                contains_synthetic_media=True,
            )
            if not youtube_id:
                raise RuntimeError("YouTube upload failed")
            result["youtube_id"] = youtube_id
            if srt_path.exists():
                upload_captions(youtube_id, srt_path, language=YOUTUBE_LANGUAGE)
            schedule_video(
                youtube_id,
                publish_at.isoformat(),
                made_for_kids=False,
                contains_synthetic_media=True,
            )
            logger.info("Video scheduled successfully: %s for %s", youtube_id, publish_at.isoformat())
        else:
            logger.info("Upload skipped (--dry-run / --no-upload active)")

        if not dry_run:
            record_sleep_topic(SLEEP_HISTORY, selected_id)
        result["success"] = True
    except Exception as error:
        logger.exception("Sleep pipeline failed")
        result["errors"].append(str(error))
    finally:
        result["elapsed_minutes"] = round((time.time() - started) / 60, 2)
        _write_json(run_root / "result.json", result)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Spiritus Sleep & Ambient Bible Meditation Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Build everything without upload")
    parser.add_argument("--no-upload", action="store_true", help="Build without upload")
    parser.add_argument("--topic-id", choices=None, help="Specific curated sleep topic id")
    parser.add_argument("--duration", type=int, default=None, help="Custom duration in seconds (e.g. 600 for quick test)")
    parser.add_argument("--history", action="store_true", help="Show sleep topic history")
    args = parser.parse_args()

    if args.history:
        print("Used sleep topics:")
        for item in load_sleep_history(SLEEP_HISTORY):
            print(f"- {item}")
        print("\nAvailable catalog:")
        for tid, tinfo in SLEEP_TOPICS.items():
            print(f"- {tid}: {tinfo['title_seed']} ({tinfo['bible_passage']})")
        return 0

    res = run_sleep_pipeline(
        upload=not args.no_upload,
        dry_run=args.dry_run or args.no_upload,
        topic_id=args.topic_id,
        duration=args.duration,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
