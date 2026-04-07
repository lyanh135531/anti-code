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
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY",    "YOUR_GEMINI_API_KEY")
PEXELS_API_KEY    = os.getenv("PEXELS_API_KEY",    "YOUR_PEXELS_API_KEY")
PIXABAY_API_KEY   = os.getenv("PIXABAY_API_KEY",   "YOUR_PIXABAY_API_KEY")

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
# CÀI ĐẶT VIDEO CHÍNH (16:9)
# ============================================================
VIDEO_WIDTH    = 1920
VIDEO_HEIGHT   = 1080
FPS            = 24
IMAGE_DURATION = 6       # Giây mỗi ảnh (tăng lên nếu ảnh ít)
FADE_DURATION  = 0.8     # Giây fade chuyển cảnh
MAX_IMAGES     = 10      # Số ảnh tối đa mỗi video

# ============================================================
# CÀI ĐẶT YOUTUBE SHORTS (9:16)
# ============================================================
SHORTS_WIDTH   = 1080
SHORTS_HEIGHT  = 1920
SHORTS_DURATION = 58     # Giây (giữ dưới 60s để đủ điều kiện Shorts)

# ============================================================
# CÀI ĐẶT GIỌNG ĐỌC (Edge TTS - Microsoft, miễn phí)
# ============================================================
TTS_VOICE = "en-US-AriaNeural"
# Gợi ý giọng khác:
# "en-US-GuyNeural"        - Giọng nam Mỹ
# "en-GB-SoniaNeural"      - Giọng nữ Anh
# "en-AU-NatashaNeural"    - Giọng nữ Úc
# "en-IN-NeerjaNeural"     - Giọng nữ Ấn Độ (phù hợp topic Eastern)
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
# CHỦ ĐỀ VIDEO (Pipeline tự động xoay vòng)
# ============================================================
RELIGION_TOPICS = [
    {
        "topic": "The Most Powerful Prayers in Christianity",
        "religion": "Christianity",
        "keywords": ["prayer", "christianity", "faith", "god", "powerful prayers"],
        "script_angle": "Explore the most profound Christian prayers and their spiritual significance",
        "shorts_hook": "The prayer Jesus said only you should know"
    },
    {
        "topic": "Sacred Bible Stories That Will Restore Your Faith",
        "religion": "Christianity",
        "keywords": ["bible", "christianity", "faith", "stories", "miracles"],
        "script_angle": "Retell 3 Bible stories with deep spiritual meanings for today's world",
        "shorts_hook": "The Bible story that scientists can't explain"
    },
    {
        "topic": "The Hidden Symbolism of the Cross",
        "religion": "Christianity",
        "keywords": ["cross", "christianity", "symbolism", "jesus", "sacred"],
        "script_angle": "Explain the deep historical and spiritual symbolism of the Christian cross",
        "shorts_hook": "What does the cross REALLY mean in Christianity?"
    },
    {
        "topic": "Biblical Miracles That Defy Explanation",
        "religion": "Christianity",
        "keywords": ["miracles", "bible", "christianity", "faith", "unexplained"],
        "script_angle": "Describe 5 famous biblical miracles and examine their enduring spiritual impact",
        "shorts_hook": "Scientists tried to debunk this miracle and failed"
    },
    {
        "topic": "The Secret History of the Dead Sea Scrolls",
        "religion": "Christianity",
        "keywords": ["dead sea scrolls", "bible", "christianity", "history", "ancient"],
        "script_angle": "Discuss the discovery of the Dead Sea Scrolls and how they changed our understanding of the Bible",
        "shorts_hook": "What the Dead Sea Scrolls revealed about the Bible"
    },
    {
        "topic": "Angels in the Bible: What Do They Really Look Like?",
        "religion": "Christianity",
        "keywords": ["angels", "bible", "christianity", "seraphim", "cherubim"],
        "script_angle": "Explore the biblical descriptions of angels, clearing up modern misconceptions",
        "shorts_hook": "Biblically accurate angels will terrify you"
    },
    {
        "topic": "The Seven Deadly Sins and Their Heavenly Virtues",
        "religion": "Christianity",
        "keywords": ["seven deadly sins", "virtues", "christianity", "morality", "faith"],
        "script_angle": "Break down the historical concept of the seven deadly sins and counter them with the seven heavenly virtues",
        "shorts_hook": "The sin you commit every single day"
    },
    {
        "topic": "Who Were the 12 Apostles? Real History Uncovered",
        "religion": "Christianity",
        "keywords": ["apostles", "disciples", "jesus", "christianity", "bible history"],
        "script_angle": "Trace the actual historical lives and fates of Jesus' twelve core disciples",
        "shorts_hook": "The brutal fate of Jesus' 12 apostles"
    },
]
