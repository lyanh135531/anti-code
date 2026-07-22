# YouTube Shorts AI Pipeline

Repository này chứa hai pipeline tự động tạo một YouTube Short mỗi ngày:

- `youtube-auto`: nội dung về Chúa Jesus và Kinh Thánh, kênh mặc định `Spiritus`.
- `youtube-stoicism`: nội dung về Stoicism, kênh mặc định `Stoicism Mind`.

Mỗi pipeline tự tạo chủ đề, kịch bản 9 cảnh, SEO, giọng đọc, 9 ảnh dọc, video có phụ đề và upload/lên lịch trên YouTube.

## Kiến trúc AI

| Công đoạn | Provider | Model mặc định |
|---|---|---|
| Topic, script và SEO | Google Gemini | `gemini-3.1-flash-lite` |
| Text fallback | Cloudflare Workers AI | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| Ảnh | Cloudflare Workers AI | `@cf/black-forest-labs/flux-2-klein-4b` |
| Voice và subtitle | Edge TTS | `en-US-AndrewMultilingualNeural` |
| Dựng video | MoviePy + Pillow + FFmpeg | 1080x1920, 24 FPS |

Gemini được retry trước. Cloudflare text chỉ được gọi nếu Gemini đã thất bại hoặc không được cấu hình. Ảnh luôn dùng Cloudflare; dự án không dùng Pollinations, Pexels hoặc Pixabay.

Riêng `youtube-auto`, prompt nội dung dùng cấu trúc giữ chân 9 cảnh: hook ngắn, mâu thuẫn tăng dần, khám phá từ một đoạn Kinh Thánh, payoff thực tế và câu hỏi bình luận. Metadata tránh testimony giả, fearbait và các tiêu đề hứa quá mức. Prompt ảnh được chuẩn hóa thành tranh sơn dầu bán trừu tượng: nét impasto, nhân vật hoàn toàn không có chi tiết khuôn mặt, bố cục tượng hình và bảng màu vàng cổ–hổ phách–cam cháy như cuối hoàng hôn.

## Yêu cầu

- Windows 10/11 hoặc Linux có Docker.
- Python 3.11 hoặc 3.12.
- FFmpeg có trong `PATH` nếu chạy trực tiếp bằng Python.
- Tài khoản Google AI Studio.
- Tài khoản Cloudflare có Workers AI.
- Google Cloud OAuth credentials nếu muốn upload lên YouTube.

## 1. Tạo Gemini API key

1. Mở [Google AI Studio API Keys](https://aistudio.google.com/app/apikey).
2. Đăng nhập và chọn **Create API key**.
3. Chọn hoặc tạo Google Cloud project.
4. Sao chép key và lưu vào password manager. Không đưa key lên Git.

Gemini là text provider chính. Nếu Gemini hết quota hoặc tạm lỗi, pipeline sẽ tự chuyển sang Cloudflare Llama.

## 2. Tạo Cloudflare Workers AI token

1. Đăng nhập [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Mở **Workers & Pages** → **Workers AI**.
3. Chọn **Use REST API**.
4. Chọn **Create a Workers AI API Token**.
5. Xác nhận token có quyền `Workers AI - Read` và `Workers AI - Edit`.
6. Sao chép cả **API Token** và **Account ID** trên màn hình REST API.

Token này được dùng cho text fallback và toàn bộ 9 ảnh. Gói Workers AI Free hiện có hạn mức miễn phí reset hằng ngày; kiểm tra mức sử dụng thực tế trong Workers AI Dashboard.

## 3. Cấu hình môi trường

Mỗi pipeline đọc file `.env` trong chính thư mục của nó. Tạo file từ mẫu:

```powershell
Copy-Item youtube-auto/.env.example youtube-auto/.env
Copy-Item youtube-stoicism/.env.example youtube-stoicism/.env
```

Nếu `.env` đã tồn tại, không copy đè file. Hãy thêm các biến bên dưới vào file hiện tại. `POLLINATIONS_API_KEY`, `PEXELS_API_KEY` và `PIXABAY_API_KEY` cũ không còn được đọc.

Điền cùng bộ AI credentials vào từng file cần chạy:

```env
GEMINI_API_KEY=AIza_your_real_key
GEMINI_TEXT_MODEL=gemini-3.1-flash-lite

CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_workers_ai_token
CLOUDFLARE_TEXT_MODEL=@cf/meta/llama-3.3-70b-instruct-fp8-fast
CLOUDFLARE_IMAGE_MODEL=@cf/black-forest-labs/flux-2-klein-4b
```

Chỉ `GEMINI_API_KEY` có thể bỏ trống: khi đó text sẽ dùng Cloudflare ngay từ đầu. Cloudflare Account ID và token là bắt buộc vì không có image fallback.

Các file `.env`, `client_secrets.json` và `youtube_token.pickle` đã được loại khỏi Git. Không đặt credential trực tiếp trong `config.py`.

## 4. Cài Python và FFmpeg trên Windows

Cài FFmpeg, sau đó xác nhận:

```powershell
ffmpeg -version
```

Tạo môi trường riêng cho từng pipeline. Ví dụ với `youtube-auto`:

```powershell
Set-Location C:\Project\anti-code\youtube-auto
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Lặp lại trong `youtube-stoicism` nếu muốn chạy hai bot bằng hai môi trường độc lập. Không cài dependency ở global Python.

## 5. Chạy thử không upload

Trong thư mục pipeline đã chọn:

```powershell
python main.py --dry-run
```

`--dry-run` vẫn gọi Gemini/Cloudflare, tạo audio, 9 ảnh và render MP4; nó chỉ bỏ bước upload. Kết quả nằm trong:

```text
output/scripts/
output/audio/
output/images/<video_id>/
output/shorts/
logs/
```

Các lệnh hỗ trợ:

```powershell
python main.py --help
python main.py --history
python main.py --channel
python main.py --no-upload
python main.py --schedule 19
```

## 6. Cấu hình YouTube OAuth

Bỏ qua bước này nếu chỉ dùng `--dry-run` hoặc `--no-upload`.

1. Mở [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo hoặc chọn project.
3. Vào **APIs & Services** → **Library**, bật **YouTube Data API v3**.
4. Cấu hình **OAuth consent screen**. Nếu app ở chế độ Testing, thêm tài khoản YouTube vào Test users.
5. Vào **Credentials** → **Create credentials** → **OAuth client ID**.
6. Chọn loại **Desktop app** và tải JSON.
7. Đổi tên file thành `client_secrets.json`, đặt cạnh `main.py` trong từng pipeline cần upload.

Chạy lần đầu:

```powershell
python main.py --channel
```

Trình duyệt sẽ mở để cấp quyền. Token được lưu thành `youtube_token.pickle`. Nếu chạy cả hai pipeline, có thể dùng cùng `client_secrets.json`, nhưng mỗi thư mục giữ token riêng.

## 7. Chạy hằng ngày

### Scheduler Python

Giờ chạy và giờ publish nằm trong `scheduler.py`:

```python
PIPELINE_RUN_HOUR = "17:00"
PUBLISH_HOUR = 19
UPLOAD_IMMEDIATELY = False
```

Khởi động scheduler:

```powershell
python scheduler.py
```

Chạy ngay một lần khi scheduler khởi động:

```powershell
$env:RUN_NOW = "true"
python scheduler.py
```

Timezone Docker mặc định là `Asia/Ho_Chi_Minh`. Khi chạy trực tiếp, scheduler dùng timezone của hệ điều hành.

### Windows Task Scheduler

Tạo Daily Task với:

- Program: `C:\Project\anti-code\youtube-auto\.venv\Scripts\python.exe`
- Arguments: `main.py --schedule 19`
- Start in: `C:\Project\anti-code\youtube-auto`

Thay đường dẫn bằng `youtube-stoicism` cho bot còn lại.

## 8. Chạy bằng Docker

Trong thư mục pipeline:

```powershell
docker compose build
docker compose up -d
docker compose logs -f
```

Container mặc định chạy `scheduler.py`. File `.env`, OAuth credentials, token và output được đọc qua volume hiện có. Thực hiện OAuth lần đầu bằng Python trên máy host trước khi chạy container vì container không thuận tiện mở trình duyệt.

## Tùy chỉnh

Các thiết lập nội dung và video nằm trong `config.py` của từng pipeline:

- `CHANNEL_NAME`, `BASE_TAGS`, `TARGET_RELIGION`.
- `TTS_VOICE`, `TTS_RATE`, `TTS_PITCH`.
- `YOUTUBE_PRIVACY`, `YOUTUBE_LANGUAGE`, `YOUTUBE_CATEGORY`.
- `SHORTS_MAX_IMAGES`, kích thước và FPS.

Có thể đổi model qua `.env` mà không sửa source. Chỉ dùng model Cloudflare hỗ trợ OpenAI-compatible chat/JSON cho `CLOUDFLARE_TEXT_MODEL`, và model có multipart text-to-image tương thích cho `CLOUDFLARE_IMAGE_MODEL`.

Nhạc nền là tùy chọn. Đặt `.mp3` hoặc `.wav` vào `assets/music/` của pipeline tương ứng.

## Xử lý lỗi

| Lỗi/log | Cách kiểm tra |
|---|---|
| `GEMINI_API_KEY is not configured` | Điền Gemini key; pipeline vẫn dùng Cloudflare text nếu Cloudflare hợp lệ. |
| `Gemini failed; trying Cloudflare fallback` | Gemini đã retry thất bại; xem HTTP status kế bên và quota trong AI Studio. |
| Cloudflare `401` | API token sai hoặc đã bị thu hồi. |
| Cloudflare `403` | Token thiếu quyền Workers AI hoặc model không khả dụng cho account. |
| Cloudflare `429` | Hết quota/rate limit; xem Workers AI Dashboard và chờ kỳ reset. |
| `result.image` bị thiếu | Kiểm tra model ID có đúng FLUX.2 Klein 4B hay không. |
| `ffmpeg not found` | Cài FFmpeg và mở terminal mới sau khi cập nhật `PATH`. |
| `client_secrets.json` không tồn tại | Làm lại bước YouTube OAuth hoặc chạy `--no-upload`. |
| OAuth token lỗi/đổi scope | Xóa `youtube_token.pickle`, sau đó xác thực lại. |
| Audio dài hơn 58 giây | Chạy lại để tạo script khác hoặc giảm giới hạn từ trong `script_gen.py`. |

Log lỗi provider bao gồm HTTP status và phần đầu response body, nhưng không ghi API key/token.

## Lưu ý vận hành

- Không chạy đồng thời hai instance của cùng một pipeline vì có thể trùng lịch sử topic hoặc output ID.
- Kiểm tra vài video đầu bằng `--dry-run` trước khi bật scheduler.
- Nội dung dùng template lặp lại có thể ảnh hưởng điều kiện kiếm tiền của YouTube; nên kiểm tra chất lượng và tính khác biệt trước khi public.
- Khai báo nội dung tổng hợp/AI trong YouTube Studio khi hình ảnh có vẻ chân thực và thuộc trường hợp YouTube yêu cầu disclosure.
