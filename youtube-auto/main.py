"""
==========================================================
  YOUTUBE AUTO PIPELINE - MAIN ORCHESTRATOR
  
  Chạy: python main.py
  
  Pipeline đầy đủ:
    1. Chọn chủ đề (xoay vòng tự động)
    2. Tạo script bằng Gemini AI
    3. Chuyển script thành giọng đọc (Edge TTS)
    4. Tải ảnh từ Pexels + Pixabay
    5. Dựng video 1920x1080 với Ken Burns effect
    6. Tạo thumbnail đẹp 1280x720
    7. Tạo YouTube Shorts 1080x1920
    8. Tối ưu SEO (title, description, tags)
    9. Upload lên YouTube tự động
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

# ── Import config ───────────────────────────────────────────
from config import (
    TARGET_RELIGION, OUTPUT_DIR, MUSIC_DIR,
    TTS_VOICE, TTS_RATE, TTS_PITCH,
    IMAGE_DURATION, FADE_DURATION, MAX_IMAGES,
    FPS, VIDEO_WIDTH, VIDEO_HEIGHT,
    CHANNEL_NAME, YOUTUBE_CATEGORY, YOUTUBE_LANGUAGE, YOUTUBE_PRIVACY,
)

# ── Import modules ────────────────────────────────────────--
from modules.script_gen    import generate_video_script, generate_shorts_script, save_script
from modules.tts           import text_to_speech, get_audio_duration
from modules.image_fetch   import fetch_images_for_topic
from modules.video_maker   import build_video
from modules.thumbnail_maker import create_thumbnail
from modules.shorts_maker  import create_shorts_from_images
from modules.seo_optimizer import generate_seo_metadata, format_description_for_youtube
from modules.uploader      import upload_video, upload_shorts, get_channel_info





def _get_background_music() -> str | None:
    """Tìm file nhạc nền trong thư mục assets/music/."""
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    if music_files:
        # Xoay vòng nhạc theo ngày
        idx = datetime.now().day % len(music_files)
        chosen = str(music_files[idx])
        logger.info(f"Nhạc nền: {music_files[idx].name}")
        return chosen
    logger.info("Không có nhạc nền trong assets/music/ — bỏ qua")
    return None


def _generate_video_id(topic_config: dict) -> str:
    """Tạo ID duy nhất cho video."""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    rel = topic_config.get("religion", "world")[:3].lower()
    return f"{rel}_{ts}"


# ============================================================
# PIPELINE CHÍNH
# ============================================================

def run_pipeline(
    upload:       bool = True,
    make_shorts:  bool = True,
    dry_run:      bool = False,     # True = chỉ tạo file, không upload
    schedule_hour:int  = None,      # Lên lịch đăng lúc X giờ (VD: 18)
) -> dict:
    """
    Chạy toàn bộ pipeline tạo video.
    
    Args:
        upload:       Upload lên YouTube sau khi tạo
        make_shorts:  Tạo YouTube Shorts kèm theo
        dry_run:      Tạo file nhưng không upload
        schedule_hour: Giờ lên lịch đăng (0-23, None = đăng ngay)
        
    Returns:
        Dict kết quả pipeline
    """
    start_time = time.time()
    results = {
        "success":       False,
        "video_id":      None,
        "shorts_id":     None,
        "video_path":    None,
        "thumbnail_path":None,
        "shorts_path":   None,
        "metadata":      None,
        "errors":        [],
    }

    logger.info("=" * 60)
    logger.info("  🚀 BẮT ĐẦU PIPELINE YOUTUBE AUTO")
    logger.info("=" * 60)

    # ── BƯỚC 0: Chọn Topic ────────────────────────────────
    from modules.idea_gen import generate_new_topic

    topic_config = generate_new_topic(TARGET_RELIGION)
    video_id    = _generate_video_id(topic_config)

    logger.info(f"📌 Topic: {topic_config['topic']}")
    logger.info(f"📖 Religion: {topic_config['religion']}")
    logger.info(f"🆔 Video ID: {video_id}")

    # ── BƯỚC 1: Tạo Script ────────────────────────────────
    logger.info("\n[1/9] 📝 Tạo nội dung script...")
    try:
        script_data  = generate_video_script(topic_config)
        main_script  = script_data["script"]

        # Lưu script
        script_path = OUTPUT_DIR / "scripts" / f"{video_id}.txt"
        save_script(main_script, video_id, OUTPUT_DIR / "scripts")
        logger.info(f"  ✅ Script: {script_data['word_count']} từ")
    except Exception as e:
        logger.error(f"  ❌ Lỗi tạo script: {e}")
        results["errors"].append(f"Script: {e}")
        return results

    # ── BƯỚC 2: SEO Metadata ─────────────────────────────
    logger.info("\n[2/9] 🔍 Tạo SEO metadata...")
    try:
        seo_meta = generate_seo_metadata(topic_config, main_script)
        seo_meta["description"] = format_description_for_youtube(seo_meta["description"])
        results["metadata"] = seo_meta
        logger.info(f"  ✅ Title: {seo_meta['title']}")
        logger.info(f"  ✅ Tags: {len(seo_meta['tags'])} tags")
    except Exception as e:
        logger.warning(f"  ⚠️ SEO lỗi (dùng fallback): {e}")
        # Dùng title từ topic_config
        seo_meta = {
            "title":              topic_config["topic"][:100],
            "description":        main_script[:300] + "...",
            "tags":               topic_config.get("keywords", []),
            "shorts_title":       topic_config["topic"][:50] + " #Shorts",
            "shorts_description": topic_config["topic"],
        }

    # ── BƯỚC 3: Text-to-Speech (Video dài) ───────────────
    logger.info("\n[3/9] 🗣️ Tạo giọng đọc (video dài)...")
    try:
        audio_main_path = str(OUTPUT_DIR / "audio" / f"{video_id}_main.mp3")
        text_to_speech(
            script    = main_script,
            output_path = audio_main_path,
            voice     = TTS_VOICE,
            rate      = TTS_RATE,
            pitch     = TTS_PITCH,
        )
        audio_dur = get_audio_duration(audio_main_path)
        logger.info(f"  ✅ Audio: {audio_dur:.1f}s ({audio_main_path})")
    except Exception as e:
        logger.error(f"  ❌ Lỗi TTS: {e}")
        results["errors"].append(f"TTS: {e}")
        return results

    # ── BƯỚC 4: Tải Ảnh ──────────────────────────────────
    logger.info("\n[4/9] 🖼️ Tải ảnh từ Pexels + Pixabay...")
    try:
        img_dir = OUTPUT_DIR / "images" / video_id
        img_dir.mkdir(parents=True, exist_ok=True)

        image_paths = fetch_images_for_topic(
            topic_config = topic_config,
            output_dir   = img_dir,
            max_images   = MAX_IMAGES,
            video_id     = video_id,
        )

        if not image_paths:
            raise RuntimeError("Không tải được ảnh nào!")

        logger.info(f"  ✅ Tải được {len(image_paths)} ảnh")
    except Exception as e:
        logger.error(f"  ❌ Lỗi tải ảnh: {e}")
        results["errors"].append(f"Images: {e}")
        return results

        # ── BƯỚC 5: Tạo Thumbnail ────────────────────────────
    logger.info("\n[5/9] 🎨 Tạo thumbnail...")
    thumbnail_path = None
    try:
        thumb_out = str(OUTPUT_DIR / "thumbnails" / f"{video_id}_thumb.jpg")
        
        # Tối ưu title cho thumbnail: Xóa tên channel nếu AI lỡ viết vào
        display_title = seo_meta.get("title", topic_config["topic"])
        for suffix in [f" | {CHANNEL_NAME}", f" - {CHANNEL_NAME}", f"|{CHANNEL_NAME}", f"-{CHANNEL_NAME}"]:
            if display_title.endswith(suffix):
                display_title = display_title[:-len(suffix)].strip()

        thumbnail_path = create_thumbnail(
            image_path  = image_paths[0],
            title       = display_title,
            religion    = topic_config["religion"],
            output_path = thumb_out,
            subtitle    = "", # Đã xóa subtitle theo yêu cầu
        )
        results["thumbnail_path"] = thumbnail_path
        logger.info(f"  ✅ Thumbnail: {thumb_out}")
    except Exception as e:
        logger.warning(f"  ⚠️ Thumbnail lỗi (bỏ qua): {e}")
        results["errors"].append(f"Thumbnail: {e}")

    # ── BƯỚC 6: Dựng Video Chính ─────────────────────────
    logger.info("\n[6/9] 🎬 Dựng video chính (1920x1080)...")
    video_path = None
    try:
        music_path = _get_background_music()
        video_out  = str(OUTPUT_DIR / "videos" / f"{video_id}_video.mp4")

        video_path = build_video(
            image_paths   = image_paths,
            audio_path    = audio_main_path,
            output_path   = video_out,
            channel_name  = CHANNEL_NAME,
            music_path    = music_path,
            music_volume  = 0.08,
            img_duration  = IMAGE_DURATION,
            fade_duration = FADE_DURATION,
            W             = VIDEO_WIDTH,
            H             = VIDEO_HEIGHT,
            fps           = FPS,
            vtt_path      = audio_main_path.replace(".mp3", ".srt"),
        )
        results["video_path"] = video_path
        size_mb = Path(video_path).stat().st_size / 1024 / 1024
        logger.info(f"  ✅ Video: {size_mb:.1f} MB")
    except Exception as e:
        logger.error(f"  ❌ Lỗi dựng video: {e}")
        results["errors"].append(f"Video: {e}")
        return results

    # ── BƯỚC 7: Tạo YouTube Shorts ───────────────────────
    shorts_path = None
    if make_shorts:
        logger.info("\n[7/9] ⚡ Tạo YouTube Shorts (1080x1920)...")
        try:
            # Tạo script ngắn cho Shorts
            shorts_script = generate_shorts_script(topic_config, main_script)
            save_script(shorts_script, f"{video_id}_shorts", OUTPUT_DIR / "scripts")

            # TTS cho Shorts (nhanh hơn, giọng hơi nhanh)
            shorts_audio_path = str(OUTPUT_DIR / "audio" / f"{video_id}_shorts.mp3")
            text_to_speech(
                script      = shorts_script,
                output_path = shorts_audio_path,
                voice       = TTS_VOICE,
                rate        = "+5%",   # Nhanh hơn chút cho Shorts
                pitch       = TTS_PITCH,
            )

            # Tạo video Shorts từ ảnh (nhanh hơn từ video gốc)
            shorts_out = str(OUTPUT_DIR / "shorts" / f"{video_id}_shorts.mp4")
            shorts_path = create_shorts_from_images(
                image_paths  = image_paths[:6],  # Dùng 6 ảnh đầu
                audio_path   = shorts_audio_path,
                output_path  = shorts_out,
                channel_name = CHANNEL_NAME,
                fps          = FPS,
                vtt_path     = shorts_audio_path.replace(".mp3", ".srt"),
            )
            results["shorts_path"] = shorts_path
            logger.info(f"  ✅ Shorts: {shorts_out}")
        except Exception as e:
            logger.warning(f"  ⚠️ Shorts lỗi (bỏ qua): {e}")
            results["errors"].append(f"Shorts: {e}")

    # ── BƯỚC 8: Tính giờ đăng ────────────────────────────
    publish_at = None
    if schedule_hour is not None:
        # Lên lịch đăng vào giờ cụ thể hôm nay (hoặc ngày mai nếu đã qua)
        tz_offset = timedelta(hours=7)   # GMT+7 (Việt Nam)
        tz        = timezone(tz_offset)
        now       = datetime.now(tz)
        publish   = now.replace(hour=schedule_hour, minute=0, second=0, microsecond=0)
        if publish <= now:
            publish += timedelta(days=1)
        publish_at = publish.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        logger.info(f"  📅 Lên lịch đăng: {publish_at}")

    # ── BƯỚC 9: Upload YouTube ────────────────────────────
    if upload and not dry_run:
        logger.info("\n[9/9] 📤 Upload lên YouTube...")

        # Upload video chính
        if video_path:
            try:
                vid_id = upload_video(
                    video_path     = video_path,
                    thumbnail_path = thumbnail_path,
                    title          = seo_meta["title"],
                    description    = seo_meta["description"],
                    tags           = seo_meta["tags"],
                    category_id    = YOUTUBE_CATEGORY,
                    language       = YOUTUBE_LANGUAGE,
                    privacy        = YOUTUBE_PRIVACY,
                    publish_at     = publish_at,
                )
                results["video_id"] = vid_id
                if vid_id:
                    logger.info(f"  ✅ Video upload OK: https://youtube.com/watch?v={vid_id}")
                else:
                    logger.error("  ❌ Upload video thất bại!")
            except Exception as e:
                logger.error(f"  ❌ Upload video lỗi: {e}")
                results["errors"].append(f"Upload video: {e}")

        # Upload Shorts
        if shorts_path and make_shorts:
            try:
                # Đăng shorts 30 phút sau video chính
                shorts_publish = None
                if publish_at:
                    pub_dt = datetime.fromisoformat(publish_at)
                    shorts_pub_dt = pub_dt + timedelta(minutes=30)
                    shorts_publish = shorts_pub_dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")

                sh_id = upload_shorts(
                    video_path   = shorts_path,
                    title        = seo_meta.get("shorts_title", seo_meta["title"][:50] + " #Shorts"),
                    description  = seo_meta.get("shorts_description", ""),
                    tags         = seo_meta["tags"][:15],
                    privacy      = YOUTUBE_PRIVACY,
                    publish_at   = shorts_publish,
                )
                results["shorts_id"] = sh_id
                if sh_id:
                    logger.info(f"  ✅ Shorts upload OK: https://youtube.com/watch?v={sh_id}")
                else:
                    logger.error("  ❌ Upload Shorts thất bại!")
            except Exception as e:
                logger.warning(f"  ⚠️ Upload Shorts lỗi: {e}")
                results["errors"].append(f"Upload shorts: {e}")
    else:
        if dry_run:
            logger.info("\n[9/9] 🔍 Dry run mode — bỏ qua upload")
        else:
            logger.info("\n[9/9] ⏭️ Upload bị tắt (--no-upload)")

    # ── TỔNG KẾT ─────────────────────────────────────────
    elapsed = time.time() - start_time
    results["success"] = bool(video_path)

    logger.info("\n" + "=" * 60)
    logger.info("  📊 KẾT QUẢ PIPELINE")
    logger.info("=" * 60)
    logger.info(f"  ⏱️  Thời gian: {elapsed/60:.1f} phút")
    logger.info(f"  📌 Topic: {topic_config['topic'][:55]}...")
    logger.info(f"  🎬 Video: {results['video_path'] or 'N/A'}")
    logger.info(f"  🖼️  Thumbnail: {results['thumbnail_path'] or 'N/A'}")
    logger.info(f"  ⚡ Shorts: {results['shorts_path'] or 'N/A'}")
    logger.info(f"  🆔 YouTube ID: {results['video_id'] or 'Chưa upload'}")
    if results["errors"]:
        logger.warning(f"  ⚠️  Lỗi nhỏ: {', '.join(results['errors'])}")
    logger.info("=" * 60)

    # Lưu kết quả ra JSON
    result_file = LOG_DIR / f"result_{video_id}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        save_data = {k: v for k, v in results.items() if k != "metadata"}
        if results.get("metadata"):
            save_data["title"] = results["metadata"].get("title", "")
            save_data["tags_count"] = len(results["metadata"].get("tags", []))
        save_data["topic"]   = topic_config["topic"]
        save_data["elapsed_min"] = round(elapsed / 60, 1)
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return results


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="🎬 YouTube Auto Pipeline — Tự động tạo & upload video tôn giáo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Chạy pipeline đầy đủ (topic tự động)
  python main.py --topic 0               # Chọn topic #0 (Buddhism Meditation)
  python main.py --dry-run               # Tạo file nhưng KHÔNG upload
  python main.py --no-shorts             # Bỏ qua Shorts
  python main.py --no-upload             # Không upload lên YouTube
  python main.py --schedule 18           # Lên lịch đăng lúc 18:00
  python main.py --list-topics           # Xem danh sách topics
  python main.py --check-channel         # Kiểm tra thông tin kênh
        """
    )
    
    parser.add_argument("--dry-run",      action="store_true",
                        help="Tạo file nhưng không upload YouTube")
    parser.add_argument("--no-upload",    action="store_true",
                        help="Không upload YouTube")
    parser.add_argument("--no-shorts",    action="store_true",
                        help="Bỏ qua tạo YouTube Shorts")
    parser.add_argument("--schedule",     type=int, default=None, metavar="HOUR",
                        help="Lên lịch đăng lúc giờ này (0-23, VD: 18 = 6pm)")
    parser.add_argument("--list-topics",  action="store_true",
                        help="Hiện danh sách chủ đề và thoát")
    parser.add_argument("--check-channel",action="store_true",
                        help="Kiểm tra thông tin kênh YouTube và thoát")

    args = parser.parse_args()

    # ── Hiển thị danh sách topics đã tạo ──────────────────
    if args.list_topics:
        from modules.idea_gen import _get_past_topics
        past = _get_past_topics()
        print("\n📋 DANH SÁCH LỊCH SỬ TOPICS GẦN ĐÂY:\n" + "-" * 70)
        if not past:
            print("  Chưa có video nào từng được tạo.")
        else:
            for i, t in enumerate(past):
                print(f"  [{i:2d}] {t[:70]}")
        print("-" * 70)
        sys.exit(0)

    # ── Kiểm tra thông tin kênh ───────────────────────────
    if args.check_channel:
        print("\n🔍 Đang lấy thông tin kênh YouTube...")
        try:
            ch = get_channel_info()
            if ch:
                print(f"\n✅ Kênh: {ch['name']}")
                print(f"   ID: {ch['id']}")
                print(f"   Subscribers: {int(ch['subscribers']):,}")
                print(f"   Tổng video: {ch['total_videos']}")
                print(f"   Tổng views: {int(ch['total_views']):,}")
            else:
                print("❌ Không lấy được thông tin kênh")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
        sys.exit(0)

    # ── Chạy pipeline ─────────────────────────────────────
    results = run_pipeline(
        upload        = not (args.no_upload or args.dry_run),
        make_shorts   = not args.no_shorts,
        dry_run       = args.dry_run,
        schedule_hour = args.schedule,
    )

    if results["success"]:
        print("\n✅ Pipeline hoàn thành!")
        if results.get("video_id"):
            print(f"   Video: https://youtube.com/watch?v={results['video_id']}")
        if results.get("shorts_id"):
            print(f"   Shorts: https://youtube.com/watch?v={results['shorts_id']}")
    else:
        print("\n❌ Pipeline thất bại. Xem logs để biết chi tiết.")
        sys.exit(1)


if __name__ == "__main__":
    main()
