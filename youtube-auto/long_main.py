"""Spiritus independent, source-grounded YouTube long-form pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    CHANNEL_NAME,
    LONG_FPS,
    LONG_HEIGHT,
    LONG_MAX_DURATION,
    LONG_MIN_DURATION,
    LONG_MUSIC_VOLUME,
    LONG_PUBLISH_HOUR,
    LONG_PUBLISH_TIMEZONE,
    LONG_PUBLISH_WEEKDAYS,
    LONG_WIDTH,
    MUSIC_DIR,
    OUTPUT_DIR,
    TTS_PITCH,
    TTS_RATE,
    TTS_VOICE,
    YOUTUBE_CATEGORY,
    YOUTUBE_LANGUAGE,
)
from modules.long_image_gen import generate_long_images, generate_long_thumbnail
from modules.long_script_gen import (
    generate_long_script,
    generate_research_brief,
    verify_with_one_repair,
)
from modules.long_sources import build_source_pack
from modules.long_topics import load_history, record_topic, select_topic, topic_catalog_json
from modules.long_video_maker import build_long_video
from modules.tts import get_audio_duration, text_to_speech
from modules.uploader import schedule_video, upload_captions, upload_video


BASE_DIR = Path(__file__).parent
LONG_ROOT = OUTPUT_DIR / "long"
LONG_HISTORY = BASE_DIR / ".long_topic_history.txt"
LONG_LOG_DIR = BASE_DIR / "logs" / "long"
LONG_LOG_DIR.mkdir(parents=True, exist_ok=True)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

log_path = LONG_LOG_DIR / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")],
)
logger = logging.getLogger("long_pipeline")


def _video_id() -> str:
    return f"long_{datetime.now():%Y%m%d_%H%M%S}"


def next_publish_time(now: datetime | None = None) -> datetime:
    eastern = ZoneInfo(LONG_PUBLISH_TIMEZONE)
    current = now.astimezone(eastern) if now else datetime.now(eastern)
    candidates = []
    for offset in range(8):
        day = current + timedelta(days=offset)
        if day.weekday() in set(LONG_PUBLISH_WEEKDAYS):
            candidate = day.replace(hour=LONG_PUBLISH_HOUR, minute=0, second=0, microsecond=0)
            if candidate > current:
                candidates.append(candidate)
    if not candidates:
        raise RuntimeError("Could not calculate the next long-form publish time")
    return min(candidates)


def _music() -> str | None:
    files = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.wav"))
    return str(files[datetime.now().toordinal() % len(files)]) if files else None


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 60}:{value % 60:02d}"


def _chapter_lines(script: dict, audio_duration: float) -> list[str]:
    total_words = max(1, sum(len(section["narration"].split()) for section in script["sections"]))
    elapsed_words = 0
    chapters = []
    for section in script["sections"]:
        chapters.append(f"{_timestamp(audio_duration * elapsed_words / total_words)} {section['heading']}")
        elapsed_words += len(section["narration"].split())
    return chapters


def _youtube_description(script: dict, source_pack: dict, duration: float) -> str:
    sources = "\n".join(f"- {source['id']}: {source['url']}" for source in source_pack["sources"])
    return (
        f"{script.get('description', script['summary']).strip()}\n\n"
        f"Chapters\n" + "\n".join(_chapter_lines(script, duration)) + "\n\n"
        f"Official sources\n{sources}\n\n"
        "Scripture is paraphrased unless a short passage is explicitly quoted. "
        "New American Bible source material © Confraternity of Christian Doctrine. "
        "This educational reflection is not an official publication of the Catholic Church.\n\n"
        "#Catholic #Bible #Jesus #Christianity #Faith"
    )[:5000]


def _overlays(script: dict) -> list[str]:
    result: list[str] = []
    for section in script["sections"]:
        prompts = section["visual_prompts"]
        result.extend([str(section.get("on_screen_text", ""))] + [""] * (len(prompts) - 1))
    return result


def run_long_pipeline(
    upload: bool = True,
    dry_run: bool = False,
    topic_id: str | None = None,
    now: datetime | None = None,
) -> dict:
    started = time.time()
    run_id = _video_id()
    run_root = LONG_ROOT / run_id
    for name in ("sources", "scripts", "reports", "audio", "images", "thumbnails", "videos"):
        (run_root / name).mkdir(parents=True, exist_ok=True)
    result = {
        "success": False,
        "run_id": run_id,
        "topic_id": None,
        "video_path": None,
        "youtube_id": None,
        "verification_status": "NOT_RUN",
        "errors": [],
    }
    logger.info("Spiritus long-form pipeline started: %s", run_id)

    try:
        selected_id, topic = select_topic(LONG_HISTORY, topic_id)
        result["topic_id"] = selected_id
        logger.info("Topic: %s (%s)", selected_id, topic["bible_passage"])

        source_pack = build_source_pack(topic, run_root / "sources" / "source_pack.json")
        brief = generate_research_brief(topic, source_pack)
        _write_json(run_root / "sources" / "research_brief.json", brief)

        script = generate_long_script(topic, source_pack, brief)
        try:
            script, verification = verify_with_one_repair(script, source_pack)
        except Exception as verifier_error:
            script["verification_status"] = "FAIL"
            verification = {
                "status": "FAIL",
                "reason": f"Verifier unavailable or invalid: {verifier_error}",
                "claims": [],
                "required_changes": [],
                "repairs_applied": [],
            }
            _write_json(run_root / "scripts" / "script.json", script)
            _write_json(run_root / "reports" / "verification.json", verification)
            result["verification_status"] = "FAIL"
            raise RuntimeError("Accuracy verifier failed; media generation and upload are blocked") from verifier_error
        _write_json(run_root / "scripts" / "script.json", script)
        _write_json(run_root / "reports" / "verification.json", verification)
        result["verification_status"] = verification.get("status", "FAIL")
        if result["verification_status"] != "PASS":
            raise RuntimeError("Accuracy gate failed; media generation and upload are blocked")

        audio_path = run_root / "audio" / f"{run_id}.mp3"
        text_to_speech(script["narration"], audio_path, TTS_VOICE, TTS_RATE, TTS_PITCH)
        duration = get_audio_duration(audio_path)
        if not LONG_MIN_DURATION <= duration <= LONG_MAX_DURATION:
            raise RuntimeError(
                f"Narration duration must be {LONG_MIN_DURATION}-{LONG_MAX_DURATION} seconds, "
                f"got {duration:.1f}"
            )
        srt_path = audio_path.with_suffix(".srt")
        if not srt_path.exists() or srt_path.stat().st_size == 0:
            raise RuntimeError("TTS did not produce a usable SRT caption file")

        images, manifest = generate_long_images(
            script["visual_prompts"], run_root / "images", run_id
        )
        thumbnail = generate_long_thumbnail(
            script["visual_prompts"][0], script["thumbnail_text"],
            run_root / "thumbnails", run_id,
        )
        video_path = build_long_video(
            images,
            _overlays(script),
            str(audio_path),
            run_root / "videos" / f"{run_id}.mp4",
            CHANNEL_NAME,
            subtitle_path=srt_path,
            music_path=_music(),
            music_volume=LONG_MUSIC_VOLUME,
            width=LONG_WIDTH,
            height=LONG_HEIGHT,
            fps=LONG_FPS,
        )
        result.update(
            {"video_path": video_path, "audio_duration": duration, "image_manifest": manifest}
        )

        publish_at = next_publish_time(now)
        result["publish_at"] = publish_at.isoformat()
        if upload and not dry_run:
            youtube_id = upload_video(
                video_path=video_path,
                thumbnail_path=thumbnail,
                title=script["title"],
                description=_youtube_description(script, source_pack, duration),
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
            upload_captions(youtube_id, srt_path, language=YOUTUBE_LANGUAGE)
            schedule_video(
                youtube_id,
                publish_at.isoformat(),
                made_for_kids=False,
                contains_synthetic_media=True,
            )
            result["youtube_id"] = youtube_id
        else:
            logger.info("Upload skipped")

        record_topic(LONG_HISTORY, selected_id)
        result["success"] = True
    except Exception as error:
        logger.exception("Long-form pipeline failed")
        result["errors"].append(str(error))
    finally:
        result["elapsed_minutes"] = round((time.time() - started) / 60, 2)
        _write_json(run_root / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Spiritus independent Catholic long-form pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Build everything without upload")
    parser.add_argument("--no-upload", action="store_true", help="Build everything without upload")
    parser.add_argument("--topic-id", choices=None, help="Use one curated long-form topic id")
    parser.add_argument("--history", action="store_true", help="Show long-form topic history and catalog")
    args = parser.parse_args()
    if args.history:
        print("Used long-form topics:")
        for item in load_history(LONG_HISTORY):
            print(f"- {item}")
        print("\nCatalog:")
        print(topic_catalog_json())
        return 0
    result = run_long_pipeline(
        upload=not args.no_upload,
        dry_run=args.dry_run or args.no_upload,
        topic_id=args.topic_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
