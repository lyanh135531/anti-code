"""
==========================================================
  YOUTUBE AUTO PIPELINE - CẤU HÌNH CHÍNH
==========================================================
  Điền API Keys vào file .env (xem .env.example)
  Hoặc điền trực tiếp vào phần "API KEYS" dưới đây
==========================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file nếu có
load_dotenv()

# ============================================================
# API KEYS - Điền vào đây hoặc dùng file .env
# ============================================================
# KEY DUY NHẤT CẦN THIẾT — Pollinations (text + image)
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "YOUR_POLLINATIONS_API_KEY")

# Optional (không dùng trong pipeline hiện tại)
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY",   "")
PEXELS_API_KEY   = os.getenv("PEXELS_API_KEY",   "")
PIXABAY_API_KEY  = os.getenv("PIXABAY_API_KEY",  "")

# ============================================================
# ĐƯỜNG DẪN THƯ MỤC
# ============================================================
BASE_DIR       = Path(__file__).parent
OUTPUT_DIR     = BASE_DIR / "output"
ASSETS_DIR     = BASE_DIR / "assets"
FONTS_DIR      = ASSETS_DIR / "fonts"
MUSIC_DIR      = ASSETS_DIR / "music"
LOGS_DIR       = BASE_DIR / "logs"

# Tự động tạo thư mục nếu chưa có
for d in [
    OUTPUT_DIR / "scripts", OUTPUT_DIR / "audio",
    OUTPUT_DIR / "images",  OUTPUT_DIR / "videos",
    OUTPUT_DIR / "thumbnails", OUTPUT_DIR / "shorts",
    FONTS_DIR, MUSIC_DIR, LOGS_DIR
]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# CÀI ĐẶT YOUTUBE SHORTS (9:16) — SẢN PHẨM DUY NHẤT
# ============================================================
SHORTS_WIDTH      = 1080
SHORTS_HEIGHT     = 1920
SHORTS_FPS        = 24
SHORTS_MAX_IMAGES = 9        # Đúng 9 ảnh mỗi video (Pollinations limit = 10, giữ 1 dự phòng)
FADE_DURATION     = 0.5      # Giây fade chuyển cảnh
MUSIC_VOLUME      = 0.15     # Âm lượng nhạc nền cho Shorts

# Giữ lại các alias để không bị lỗi import cũ trong các module khác
FPS          = SHORTS_FPS
MAX_IMAGES   = SHORTS_MAX_IMAGES
VIDEO_WIDTH  = SHORTS_WIDTH
VIDEO_HEIGHT = SHORTS_HEIGHT

# ============================================================
# CÀI ĐẶT GIỌNG ĐỌC (Edge TTS - Microsoft, miễn phí)
# ============================================================
TTS_VOICE = "en-US-AndrewMultilingualNeural"
# Gợi ý giọng Nam (Male) tiếng Anh:
# "en-US-GuyNeural"         - Giọng nam Mỹ (Rất phổ biến, trầm ấm)
# "en-US-BrianNeural"       - Giọng nam Mỹ (Rõ ràng, chuyên nghiệp)
# "en-US-EricNeural"        - Giọng nam Mỹ (Trẻ trung)
# "en-GB-RyanNeural"        - Giọng nam Anh (Lịch lãm)
# "en-US-AndrewMultilingualNeural" - Giọng nam đa ngôn ngữ (Tốt)
# Gợi ý giọng Nữ (Female):
# "en-US-AriaNeural"       - Giọng nữ Mỹ (Mặc định)
# "en-GB-SoniaNeural"      - Giọng nữ Anh
# "en-AU-NatashaNeural"    - Giọng nữ Úc
TTS_RATE   = "-5%"    # Chậm hơn 5% cho dễ nghe
TTS_PITCH  = "+0Hz"

# ============================================================
# CÀI ĐẶT KÊNH YOUTUBE
# ============================================================
CHANNEL_NAME       = "Spiritus"   # Tên kênh của bạn
YOUTUBE_CATEGORY   = "27"                   # 27 = Education
YOUTUBE_LANGUAGE   = "en"
YOUTUBE_PRIVACY    = "public"               # "public", "unlisted", "private"
YOUTUBE_LICENSE    = "youtube"              # "youtube" hoặc "creativeCommon"

# Tags chung cho mọi video
BASE_TAGS = [
    "christianity", "jesus", "bible", "god", "faith",
    "christian", "scripture", "gospel", "holy spirit", "christ",
    "biblical", "prayer", "divine", "holy", "salvation"
]

# ============================================================
# CÀI ĐẶT THUMBNAIL
# ============================================================
THUMB_WIDTH   = 1280
THUMB_HEIGHT  = 720
THUMB_FONT_SIZE_TITLE  = 72
THUMB_FONT_SIZE_SUBTITLE = 36
THUMB_OVERLAY_ALPHA    = 140  # 0-255, độ tối của overlay

# Màu sắc thumbnail theo tôn giáo
RELIGION_COLORS = {
    "Buddhism":    {"primary": (255, 153, 0),   "secondary": (139, 69, 19)},   # Cam vàng
    "Christianity":{"primary": (30, 100, 200),  "secondary": (200, 150, 50)},  # Xanh vàng
    "Islam":       {"primary": (0, 128, 0),      "secondary": (200, 160, 0)},   # Xanh lá vàng
    "Hinduism":    {"primary": (220, 50, 50),    "secondary": (255, 140, 0)},   # Đỏ cam
    "World":       {"primary": (80, 50, 140),    "secondary": (200, 100, 50)},  # Tím cam
}

# ============================================================
# AI TEXT MODELS (Pollinations.ai) — MIỄN PHÍ, không quota
# ============================================================
# Thứ tự ưu tiên trong pollinations_text.py:
#   openai → mistral → deepseek → claude-fast → openai-fast

# ============================================================
# AI IMAGE MODELS (Pollinations.ai) — tốn Pollen
# ============================================================
AI_IMAGE_MODEL = "flux-schnell"
# Các model: "flux", "flux-schnell", "zimage", "flux-realism"

# ============================================================
# CHỦ ĐỀ VIDEO
# ============================================================
TARGET_RELIGION = "Christianity"
