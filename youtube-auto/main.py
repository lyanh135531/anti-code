"""
==========================================================
  SPIRITUS — YOUTUBE SHORTS AUTO PIPELINE
  Tự động tạo YouTube Shorts về Chúa Jesus / Kinh Thánh

  Chạy:
    python main.py            # Tạo + upload Shorts
    python main.py --dry-run  # Chỉ tạo file, không upload
    python main.py --schedule 18  # Lên lịch đăng lúc 18:00

  Pipeline (5 bước):
    1. Tạo chủ đề Shorts về Chúa Jesus (AI)
    2. Tạo script 9 cảnh + SEO metadata (AI)
    3. Tạo giọng đọc (Edge TTS)
    4. Tạo 9 ảnh Biblical (Pollinations Flux)
    5. Dựng video Shorts 9:16 + Upload YouTube
==========================================================
"""

import os
import sys
import logging
import argparse
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix UnicodeEncodeError trên Terminal Windows (cp1252 không hỗ trợ tiếng Việt/emoji)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Setup logging ──────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ]
)
logger = logging.getLogger("pipeline")

# ── Config ─────────────────────────────────────────────────
from config import (
    TARGET_RELIGION, OUTPUT_DIR, MUSIC_DIR,
    TTS_VOICE, TTS_RATE, TTS_PITCH,
    FADE_DURATION, SHORTS_MAX_IMAGES,
    SHORTS_WIDTH, SHORTS_HEIGHT, SHORTS_FPS,
    CHANNEL_NAME, YOUTUBE_CATEGORY, YOUTUBE_LANGUAGE, YOUTUBE_PRIVACY,
)

# ── Modules ─────────────────────────────────────────────────
from modules.idea_gen          import generate_new_topic
from modules.script_gen        import generate_shorts_script, save_script
from modules.tts               import text_to_speech, get_audio_duration
from modules.pollinations_image_gen import generate_shorts_images
from modules.shorts_maker      import create_shorts_from_images
from modules.seo_optimizer     import generate_seo_metadata, format_description_for_youtube
from modules.uploader          import upload_shorts, get_channel_info


# ── Helpers ─────────────────────────────────────────────────

def _get_background_music() -> str | None:
    """Tìm nhạc nền trong assets/music/."""
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    if music_files:
        idx = datetime.now().day % len(music_files)
        chosen = str(music_files[idx])
        logger.info(f"Nhạc nền: {music_files[idx].name}")
        return chosen
    return None


def _generate_video_id() -> str:
    return f"sh_{datetime.now().strftime('%Y%m%d_%H%M')}"


# ============================================================
# PIPELINE SHORTS DUY NHẤT
# ============================================================

def run_pipeline(
    upload:        bool = True,
    dry_run:       bool = False,
    schedule_hour: int  = None,
) -> dict:
    """Chạy toàn bộ Shorts pipeline."""
    start_time = time.time()
    results = {
        "success":    False,
        "shorts_id":  None,
        "shorts_path": None,
        "metadata":   None,
        "errors":     [],
    }

    logger.info("=" * 60)
    logger.info("  ✝️  SPIRITUS — SHORTS PIPELINE BẮT ĐẦU")
    logger.info("=" * 60)

    video_id = _generate_video_id()

    # ── BƯỚC 1: Tạo chủ đề ───────────────────────────────
    logger.info("\n[1/5] 💡 Tạo chủ đề về Chúa Jesus...")
    try:
        topic_config = generate_new_topic()
        logger.info(f"  ✅ Topic: {topic_config['topic']}")
        logger.info(f"  📖 Bible: {topic_config.get('bible_reference', 'N/A')}")
    except Exception as e:
        logger.error(f"  ❌ Không tạo được topic: {e}")
        results["errors"].append(f"Topic: {e}")
        return results

    # ── BƯỚC 2: Tạo script + SEO ─────────────────────────
    logger.info("\n[2/5] 📝 Tạo script Shorts (9 cảnh)...")
    try:
        script_data  = generate_shorts_script(topic_config)
        scenes       = script_data["scenes"]
        clean_script = script_data["clean_script"]
        raw_script   = script_data["script"]

        save_script(raw_script, video_id, OUTPUT_DIR / "scripts")
        logger.info(f"  ✅ Script: {script_data['word_count']} từ | {len(scenes)} cảnh")

        # SEO metadata
        seo_meta = generate_seo_metadata(topic_config, clean_script)
        seo_meta["description"] = format_description_for_youtube(seo_meta["description"])
        results["metadata"] = seo_meta
        logger.info(f"  ✅ SEO Title: {seo_meta['title'][:60]}")
    except Exception as e:
        logger.error(f"  ❌ Lỗi script/SEO: {e}")
        results["errors"].append(f"Script: {e}")
        return results

    # ── BƯỚC 3: Giọng đọc TTS ────────────────────────────
    logger.info("\n[3/5] 🗣️  Tạo giọng đọc...")
    try:
        audio_path = str(OUTPUT_DIR / "audio" / f"{video_id}.mp3")
        text_to_speech(
            script      = clean_script,
            output_path = audio_path,
            voice       = TTS_VOICE,
            rate        = TTS_RATE,
            pitch       = TTS_PITCH,
        )
        audio_dur = get_audio_duration(audio_path)
        logger.info(f"  ✅ Audio: {audio_dur:.1f}s")

        if audio_dur > 65:
            logger.warning(f"  ⚠️ Audio khá dài ({audio_dur:.1f}s) — Shorts sẽ bị cắt ở 59s")
    except Exception as e:
        logger.error(f"  ❌ Lỗi TTS: {e}")
        results["errors"].append(f"TTS: {e}")
        return results

    # ── BƯỚC 4: Tạo ảnh AI (Pollinations) ────────────────
    logger.info(f"\n[4/5] 🎨 Tạo {SHORTS_MAX_IMAGES} ảnh Biblical (Pollinations Flux)...")
    try:
        img_dir = OUTPUT_DIR / "images" / video_id
        img_dir.mkdir(parents=True, exist_ok=True)

        # Lấy đúng SHORTS_MAX_IMAGES cảnh đầu tiên
        selected_scenes = scenes[:SHORTS_MAX_IMAGES]
        # Nếu AI tạo ít cảnh hơn, lặp lại cảnh đầu để đủ số
        while len(selected_scenes) < SHORTS_MAX_IMAGES:
            selected_scenes.append(selected_scenes[0])

        image_paths = generate_shorts_images(
            scenes     = selected_scenes,
            output_dir = img_dir,
            video_id   = video_id,
        )

        if not image_paths:
            raise RuntimeError("Không tạo được ảnh nào! Kiểm tra Pollinations API key và số dư Pollen.")

        logger.info(f"  ✅ Đã tạo {len(image_paths)}/{SHORTS_MAX_IMAGES} ảnh")
    except Exception as e:
        logger.error(f"  ❌ Lỗi tạo ảnh: {e}")
        results["errors"].append(f"Images: {e}")
        return results

    # ── BƯỚC 5: Dựng Shorts ──────────────────────────────
    logger.info("\n[5/5] 🎬 Dựng YouTube Shorts (9:16)...")
    try:
        music_path  = _get_background_music()
        shorts_out  = str(OUTPUT_DIR / "shorts" / f"{video_id}.mp4")

        srt_path = audio_path.replace(".mp3", ".srt")

        shorts_path = create_shorts_from_images(
            image_paths  = image_paths,
            audio_path   = audio_path,
            output_path  = shorts_out,
            channel_name = CHANNEL_NAME,
            fps          = SHORTS_FPS,
            W            = SHORTS_WIDTH,
            H            = SHORTS_HEIGHT,
            vtt_path     = srt_path if Path(srt_path).exists() else None,
        )
        results["shorts_path"] = shorts_path
        logger.info(f"  ✅ Shorts: {shorts_path}")
    except Exception as e:
        logger.error(f"  ❌ Lỗi dựng Shorts: {e}")
        results["errors"].append(f"Shorts build: {e}")
        return results

    # ── Upload YouTube ────────────────────────────────────
    publish_at = None
    if schedule_hour is not None:
        tz     = timezone(timedelta(hours=7))
        now    = datetime.now(tz)
        pub    = now.replace(hour=schedule_hour, minute=0, second=0, microsecond=0)
        if pub <= now:
            pub += timedelta(days=1)
        publish_at = pub.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        logger.info(f"  📅 Lên lịch đăng: {publish_at}")

    if upload and not dry_run:
        logger.info("  📤 Uploading Shorts lên YouTube...")
        try:
            sh_id = upload_shorts(
                video_path  = shorts_path,
                title       = seo_meta.get("shorts_title", seo_meta["title"][:50] + " #Shorts"),
                description = seo_meta.get("shorts_description", ""),
                tags        = seo_meta["tags"][:15],
                privacy     = YOUTUBE_PRIVACY,
                publish_at  = publish_at,
            )
            results["shorts_id"] = sh_id
            if sh_id:
                logger.info(f"  ✅ Upload OK: https://youtube.com/watch?v={sh_id}")
            else:
                logger.error("  ❌ Upload thất bại")
        except Exception as e:
            logger.error(f"  ❌ Upload lỗi: {e}")
            results["errors"].append(f"Upload: {e}")
    else:
        logger.info("  ⏭️ Upload bị bỏ qua (dry-run hoặc --no-upload)")

    # ── Kết quả ──────────────────────────────────────────
    elapsed = time.time() - start_time
    results["success"] = True

    logger.info("\n" + "=" * 60)
    logger.info("  📊 KẾT QUẢ")
    logger.info("=" * 60)
    logger.info(f"  ✝️  Topic: {topic_config['topic'][:60]}")
    logger.info(f"  📖 Kinh Thánh: {script_data.get('bible_reference', 'N/A')}")
    logger.info(f"  🎥 Shorts: {results['shorts_path']}")
    logger.info(f"  🆔 YouTube ID: {results['shorts_id'] or 'Chưa upload'}")
    logger.info(f"  ⏱️  Tổng thời gian: {elapsed/60:.1f} phút")
    if results["errors"]:
        logger.warning(f"  ⚠️ Lỗi nhỏ: {', '.join(results['errors'])}")
    logger.info("=" * 60)

    # Lưu kết quả JSON
    result_file = LOG_DIR / f"result_{video_id}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        data = {k: v for k, v in results.items() if k != "metadata"}
        data["topic"]        = topic_config["topic"]
        data["bible_ref"]    = script_data.get("bible_reference", "")
        data["seo_title"]    = seo_meta.get("title", "")
        data["elapsed_min"]  = round(elapsed / 60, 1)
        json.dump(data, f, ensure_ascii=False, indent=2)

    return results


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="✝️  Spiritus — YouTube Shorts Auto Pipeline (Jesus / Christianity)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                # Chạy đầy đủ: tạo + upload Shorts
  python main.py --dry-run      # Tạo Shorts nhưng KHÔNG upload
  python main.py --no-upload    # Tạo Shorts nhưng KHÔNG upload
  python main.py --schedule 18  # Lên lịch đăng lúc 18:00 GMT+7
  python main.py --history      # Xem danh sách topics đã tạo
  python main.py --channel      # Kiểm tra thông tin kênh YouTube
        """
    )

    parser.add_argument("--dry-run",   action="store_true", help="Tạo file nhưng không upload")
    parser.add_argument("--no-upload", action="store_true", help="Không upload YouTube")
    parser.add_argument("--schedule",  type=int, default=None, metavar="HOUR",
                        help="Lên lịch đăng lúc giờ này (0-23)")
    parser.add_argument("--history",   action="store_true", help="Xem lịch sử topics đã tạo")
    parser.add_argument("--channel",   action="store_true", help="Kiểm tra thông tin kênh YouTube")

    args = parser.parse_args()

    if args.history:
        from modules.idea_gen import _get_past_topics
        past = _get_past_topics()
        print("\n📋 LỊCH SỬ TOPICS:\n" + "-" * 70)
        if not past:
            print("  Chưa có video nào từng được tạo.")
        else:
            for i, t in enumerate(past):
                print(f"  [{i+1:2d}] {t[:70]}")
        print("-" * 70)
        sys.exit(0)

    if args.channel:
        print("\n🔍 Đang lấy thông tin kênh YouTube...")
        try:
            ch = get_channel_info()
            if ch:
                print(f"\n✅ Kênh: {ch['name']}")
                print(f"   ID: {ch['id']}")
                print(f"   Subscribers: {int(ch['subscribers']):,}")
                print(f"   Tổng video: {ch['total_videos']}")
            else:
                print("❌ Không lấy được thông tin kênh")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
        sys.exit(0)

    results = run_pipeline(
        upload        = not (args.no_upload or args.dry_run),
        dry_run       = args.dry_run,
        schedule_hour = args.schedule,
    )

    if results["success"]:
        print("\n✅ Shorts đã được tạo thành công!")
        if results.get("shorts_id"):
            print(f"   🔗 https://youtube.com/watch?v={results['shorts_id']}")
        if results.get("shorts_path"):
            print(f"   📁 {results['shorts_path']}")
    else:
        print("\n❌ Pipeline thất bại. Xem logs/ để biết chi tiết.")
        sys.exit(1)


if __name__ == "__main__":
    main()
