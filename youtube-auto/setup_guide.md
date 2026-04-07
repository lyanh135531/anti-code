# 🎬 YouTube Auto Pipeline — Hướng Dẫn Cài Đặt Chi Tiết

> Pipeline tự động tạo & upload video YouTube về tôn giáo, **hoàn toàn miễn phí**.

---

## 📁 Cấu trúc thư mục

```
youtube-auto/
├── main.py                ← Chạy pipeline chính
├── scheduler.py           ← Chạy tự động hàng ngày  
├── config.py              ← Cấu hình & danh sách topics
├── requirements.txt       ← Thư viện Python cần cài
├── .env                   ← API Keys (tự tạo từ .env.example)
├── client_secrets.json    ← YouTube OAuth (tải từ Google Cloud)
├── modules/
│   ├── script_gen.py      ← Tạo nội dung bằng Gemini AI
│   ├── tts.py             ← Text-to-speech (Edge TTS)
│   ├── image_fetch.py     ← Tải ảnh Pexels + Pixabay
│   ├── video_maker.py     ← Dựng video 1920x1080
│   ├── thumbnail_maker.py ← Tạo thumbnail 1280x720
│   ├── shorts_maker.py    ← Tạo YouTube Shorts
│   ├── seo_optimizer.py   ← Tối ưu SEO tự động
│   └── uploader.py        ← Upload YouTube
├── assets/
│   └── music/             ← Thả nhạc nền .mp3 vào đây
└── output/                ← Video output tự động lưu vào đây
```

---

## 🚀 BƯỚC 1 — Cài Python và FFmpeg

### 1.1 Cài Python 3.11+

1. Vào [python.org/downloads](https://www.python.org/downloads/)
2. Tải Python 3.11 hoặc 3.12
3. Cài đặt, **tích vào "Add Python to PATH"**
4. Kiểm tra: mở CMD gõ `python --version`

### 1.2 Cài FFmpeg (bắt buộc cho MoviePy)

1. Vào [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)
2. Tải `ffmpeg-release-essentials.zip`
3. Giải nén vào `C:\ffmpeg\`
4. Thêm vào PATH:
   - Tìm "Edit the system environment variables" trong Start
   - Environment Variables → Path → New → gõ: `C:\ffmpeg\bin`
   - Nhấn OK
5. Kiểm tra: mở CMD mới gõ `ffmpeg -version`

---

## 🔑 BƯỚC 2 — Đăng ký API Keys (Tất cả miễn phí)

### 2.1 Google Gemini API Key

1. Vào [aistudio.google.com](https://aistudio.google.com)
2. Đăng nhập bằng tài khoản Google
3. Click **"Get API key"** → **"Create API key"**
4. Sao chép API key (dạng: `AIza...`)

### 2.2 Pexels API Key

1. Vào [pexels.com/api](https://www.pexels.com/api/)
2. Đăng ký tài khoản miễn phí → Click **"Your API key"**

### 2.3 Pixabay API Key

1. Vào [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Đăng ký tài khoản → Vào [pixabay.com/service/about/api](https://pixabay.com/service/about/api/)

### 2.4 Tạo file .env

Vào thư mục `youtube-auto`, tạo file tên `.env`:

```env
GEMINI_API_KEY=AIza_điền_key_của_bạn_vào_đây
PEXELS_API_KEY=điền_key_pexels_vào_đây
PIXABAY_API_KEY=điền_key_pixabay_vào_đây
```

---

## 📺 BƯỚC 3 — Cấu hình YouTube API (Quan trọng nhất)

### 3.1 Tạo Google Cloud Project

1. Vào [console.cloud.google.com](https://console.cloud.google.com)
2. Click **"Select a project"** → **"New Project"**
3. Đặt tên: `youtube-auto-pipeline` → **Create**

### 3.2 Bật YouTube Data API v3

1. Vào **"APIs & Services" → "Library"**
2. Tìm: `YouTube Data API v3` → Click → **Enable**

### 3.3 Tạo OAuth2 Credentials

1. Vào **"APIs & Services" → "Credentials"**
2. Click **"+ Create Credentials" → "OAuth client ID"**
3. Nếu chưa có OAuth consent screen:
   - **Configure consent screen** → External → Create
   - App name: `YouTube Auto Pipeline`, điền email
   - **Save and Continue** qua hết các bước
   - Ở bước "Test users": **Add Users** → thêm email Google của bạn
4. Tạo OAuth Client ID:
   - Application type: **Desktop app**
   - Name: `youtube-auto` → **Create**
5. **Download JSON** → Đổi tên thành `client_secrets.json`
6. Copy vào thư mục `youtube-auto/`

> [!IMPORTANT]
> File `client_secrets.json` phải nằm trong thư mục `youtube-auto/` cùng cấp với `main.py`

---

## 📦 BƯỚC 4 — Cài thư viện Python

Mở CMD/PowerShell:

```bash
cd c:\Project\anti-code\youtube-auto

# Tạo virtual environment (khuyến nghị)
python -m venv venv
venv\Scripts\activate

# Cài tất cả thư viện
pip install -r requirements.txt
```

Nếu gặp lỗi cài moviepy:
```bash
pip install moviepy==1.0.3
pip install imageio==2.34.0 imageio-ffmpeg==0.4.9
```

---

## 🎵 BƯỚC 5 — Thêm nhạc nền (Tùy chọn, miễn phí)

Tải nhạc nền miễn phí từ [pixabay.com/music](https://pixabay.com/music/) — Tìm: "meditation", "spiritual", "ambient"

Đặt file `.mp3` vào thư mục `assets/music/` — Pipeline tự động ghép vào video.

---

## ✏️ BƯỚC 6 — Tùy chỉnh theo kênh của bạn

Mở `config.py` và chỉnh các dòng:

```python
CHANNEL_NAME = "Sacred Wisdom Daily"   # ← Đổi thành tên kênh của bạn
TTS_VOICE    = "en-US-AriaNeural"      # Giọng đọc
YOUTUBE_PRIVACY = "public"             # Chế độ đăng
```

### Giọng đọc gợi ý:

| Giọng | Mô tả |
|-------|-------|
| `en-US-AriaNeural` | Nữ Mỹ, tự nhiên ✅ Khuyến nghị |
| `en-US-GuyNeural` | Nam Mỹ, chuyên nghiệp |
| `en-GB-SoniaNeural` | Nữ Anh, sang trọng |
| `en-AU-NatashaNeural` | Nữ Úc, dễ nghe |
| `en-IN-NeerjaNeural` | Nữ Ấn Độ (phù hợp Eastern religion) |

---

## ▶️ BƯỚC 7 — Chạy Pipeline lần đầu

```bash
# Xem danh sách topics
python main.py --list-topics

# Chạy thử KHÔNG upload (để kiểm tra trước)
python main.py --dry-run

# Chạy topic #0, không upload
python main.py --topic 0 --dry-run

# Chạy đầy đủ lần đầu (sẽ mở trình duyệt để đăng nhập Google)
python main.py --topic 0

# Chạy đầy đủ + lên lịch đăng lúc 18:00
python main.py --schedule 18
```

> [!NOTE]
> Lần đầu tiên sẽ tự động mở trình duyệt để đăng nhập Google và cấp quyền upload. Token được lưu lại — lần sau không cần đăng nhập lại.

---

## 📅 BƯỚC 8 — Tự động hóa hoàn toàn

### Cách 1: Chạy scheduler Python (giữ terminal mở)

```bash
python scheduler.py

# Hoặc chạy ngay lập tức + lên lịch hàng ngày
set RUN_NOW=true && python scheduler.py
```

### Cách 2: Windows Task Scheduler (khuyến nghị — chạy ngay cả khi tắt terminal)

1. Mở **Task Scheduler** (tìm trong Start menu)
2. Click **"Create Basic Task"**
3. Điền:
   - Name: `YouTube Auto Pipeline`
   - Trigger: **Daily** → lúc `08:00`
4. Action: **Start a program**
   - Program: `C:\Project\anti-code\youtube-auto\venv\Scripts\python.exe`
   - Arguments: `main.py --schedule 18`
   - Start in: `C:\Project\anti-code\youtube-auto`
5. **Finish**

---

## 🔧 Danh sách lệnh hữu ích

```bash
python main.py --list-topics          # Xem 18 topics có sẵn
python main.py --check-channel        # Kiểm tra thông tin kênh YouTube
python main.py                        # Chạy pipeline, topic tự động
python main.py --schedule 18          # Chạy + lên lịch đăng 18:00
python main.py --topic 5 --no-shorts  # Chọn topic #5, không làm Shorts
python main.py --dry-run              # Test pipeline, KHÔNG upload
python main.py --help                 # Xem tất cả tùy chọn
```

---

## ❓ Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `ffmpeg not found` | Chưa cài FFmpeg | Làm lại Bước 1.2 |
| `GEMINI_API_KEY invalid` | Key sai | Kiểm tra file `.env` |
| `client_secrets.json not found` | Thiếu file OAuth | Làm lại Bước 3 |
| `quota exceeded` | Hết quota ngày | Chờ 24h (Gemini reset lúc 0:00 UTC) |
| `Pexels 0 ảnh` | API key sai | Kiểm tra `PEXELS_API_KEY` |
| `Token refresh failed` | Token hết hạn | Xóa `youtube_token.pickle`, chạy lại |
| `Upload failed 403` | Thiếu permission | Kiểm tra OAuth scope trong Google Cloud |

---

## 📊 Giới hạn miễn phí hàng ngày

| Service | Giới hạn | Ghi chú |
|---------|----------|---------|
| Gemini 1.5 Flash | 1,500 req/ngày | Đủ dùng thoải mái |
| Pexels | 200 req/giờ | Đủ dùng thoải mái |
| Pixabay | 100 req/giờ | Đủ dùng thoải mái |
| YouTube Data API | 10,000 units/ngày | ~6 video upload/ngày |
| Edge TTS | Không giới hạn | Hoàn toàn miễn phí |

---

## 💡 Tips tăng view

1. **Nhạc nền nhẹ nhàng** → Tăng watch time, thuật toán ưu ái
2. **Đăng lúc 6pm VN** = 6am EST → Khán giả Mỹ/Anh đang thức dậy
3. **Đăng đều đặn 1 video/ngày** → YouTube thuật toán ưu tiên kênh đều đặn
4. **18 chủ đề xoay vòng** → Pipeline tự động, không bao giờ lặp lại topic
5. **YouTube Shorts** → Upload cùng lúc, tăng gấp đôi tiếp cận
