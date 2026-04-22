"""
==========================================================
  SCHEDULER - Chạy pipeline tự động hàng ngày
  
  Chạy 1 lần và để chạy nền:
    python scheduler.py
  
  Hoặc dùng Windows Task Scheduler để chạy lúc khởi động
==========================================================
"""

import schedule
import time
import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_DIR / "scheduler.log"), encoding="utf-8"),
    ]
)
logger = logging.getLogger("scheduler")


# ============================================================
# CÀI ĐẶT LỊCH ĐĂNG BÀI
# ============================================================

# Giờ chạy pipeline mỗi ngày (tạo video)
# Video sẽ được lên lịch đăng lúc PUBLISH_HOUR
PIPELINE_RUN_HOUR  = "17:00"   # 5 giờ chiều tạo video
PUBLISH_HOUR       = 19        # 7 giờ tối đăng lên YouTube
CREATE_SHORTS      = True      # Tạo Shorts kèm theo
UPLOAD_IMMEDIATELY = False     # False = lên lịch, True = đăng ngay


def run_daily_pipeline():
    """Chạy pipeline một lần."""
    logger.info(f"⏰ Scheduler kích hoạt lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from main import run_pipeline
        results = run_pipeline(
            upload        = True,
            make_shorts   = CREATE_SHORTS,
            dry_run       = False,
            schedule_hour = PUBLISH_HOUR if not UPLOAD_IMMEDIATELY else None,
        )

        if results["success"]:
            logger.info("✅ Pipeline hàng ngày hoàn thành!")
            if results.get("video_id"):
                logger.info(f"   Video ID: {results['video_id']}")
        else:
            logger.error("❌ Pipeline thất bại!")
            if results.get("errors"):
                for err in results["errors"]:
                    logger.error(f"   {err}")

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng trong pipeline: {e}", exc_info=True)


def main():
    logger.info("=" * 50)
    logger.info("  📅 YOUTUBE AUTO SCHEDULER ĐANG CHẠY")
    logger.info(f"  Pipeline chạy mỗi ngày lúc {PIPELINE_RUN_HOUR}")
    logger.info(f"  Video đăng lúc {PUBLISH_HOUR}:00")
    logger.info("=" * 50)

    # Lên lịch chạy hàng ngày
    schedule.every().day.at(PIPELINE_RUN_HOUR).do(run_daily_pipeline)

    # Tùy chọn: Chạy ngay lần đầu khi khởi động scheduler
    import os
    if os.getenv("RUN_NOW", "").lower() == "true":
        logger.info("RUN_NOW=true → Chạy pipeline ngay...")
        run_daily_pipeline()

    logger.info(f"⏳ Chờ đến {PIPELINE_RUN_HOUR} hàng ngày...")
    logger.info("   (Nhấn Ctrl+C để dừng scheduler)")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Kiểm tra mỗi phút


if __name__ == "__main__":
    main()
