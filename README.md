# YouTube Shorts và Facebook Reels AI Pipeline

Repository này chứa các pipeline tự động tạo video ngắn:

- `youtube-auto`: nội dung về Chúa Jesus và Kinh Thánh, đăng cùng video lên YouTube Shorts và Facebook Page Reels.
- `youtube-stoicism`: nội dung về Stoicism, kênh mặc định `Stoicism Mind`.

`youtube-auto` còn có flow long-form độc lập trong `long_main.py`: video kể chuyện
Kinh Thánh 16:9, 5–7 phút với 24–28 ảnh, dùng nguồn Vatican/USCCB và chỉ tiếp tục khi verifier
độc lập trả về `PASS`. Flow này có topic history, output, log và GitHub Actions riêng;
không lấy nội dung từ Shorts.

Chạy long-form:

```powershell
Set-Location C:\Project\anti-code\youtube-auto
.\.venv\Scripts\python.exe long_main.py --dry-run
.\.venv\Scripts\python.exe long_main.py --topic-id good-samaritan --no-upload
.\.venv\Scripts\python.exe long_main.py --history
```

Chạy không có `--dry-run`/`--no-upload` sẽ upload ở trạng thái scheduled cho 19:00
giờ US Eastern vào thứ Tư hoặc Chủ nhật gần nhất. Nếu source pack hoặc accuracy gate
không đạt, pipeline dừng trước TTS, tạo ảnh, render và upload.

Mỗi pipeline tự tạo chủ đề, kịch bản 9 cảnh, SEO, giọng đọc, 9 ảnh dọc và video có phụ đề. Riêng `youtube-auto` mặc định upload/lên lịch đồng thời trên YouTube và Facebook; lỗi ở một nền tảng không ngăn thử nền tảng còn lại.

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

# Chỉ cần trong youtube-auto
FACEBOOK_PAGE_ID=your_facebook_page_id
FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_page_access_token
FACEBOOK_GRAPH_API_VERSION=v26.0
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
python main.py --facebook-page
python main.py --no-upload
python main.py --schedule 19
python main.py --platform youtube
python main.py --platform facebook --schedule 19
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

## 7. Cấu hình Facebook Page

Facebook Graph API chỉ đăng tự động vào **Page**, không đăng vào profile cá nhân. Tài khoản tạo token phải có quyền tạo nội dung trên Page.

1. Tạo hoặc chọn app tại [Meta for Developers](https://developers.facebook.com/apps/).
2. Cấp các quyền `pages_show_list`, `pages_read_engagement` và `pages_manage_posts` cho user token của app.
3. Dùng Graph API Explorer hoặc gọi `GET /me/accounts?fields=id,name,access_token,tasks` để lấy Page ID và Page Access Token.
4. Điền `FACEBOOK_PAGE_ID` và `FACEBOOK_PAGE_ACCESS_TOKEN` vào `youtube-auto/.env`.
5. Kiểm tra mà không đăng video:

```powershell
Set-Location C:\Project\anti-code\youtube-auto
python main.py --facebook-page
```

Page token thông thường có thể hết hạn hoặc bị thu hồi. Với bot chạy lâu dài và Page thuộc Business Portfolio, nên gán Page cho một System User rồi tạo token dài hạn có đúng ba quyền trên. Nếu app phục vụ tài khoản không thuộc roles của app, Meta có thể yêu cầu App Review/Advanced Access.

Luồng upload dùng Reels Publishing API chính thức: tạo phiên, gửi file MP4 cục bộ, kiểm tra trạng thái rồi publish hoặc schedule. Token chỉ được gửi trong header và không được ghi vào log.

## 8. Chạy hằng ngày

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

Scheduler mặc định tạo một video rồi đăng lên cả YouTube Shorts và Facebook Reels. Giờ publish được tính cố định theo GMT+7; nếu thời điểm đã chọn còn dưới 10 phút, cả hai nền tảng được chuyển sang cùng giờ ngày hôm sau.

### Windows Task Scheduler

Tạo Daily Task với:

- Program: `C:\Project\anti-code\youtube-auto\.venv\Scripts\python.exe`
- Arguments: `main.py --schedule 19`
- Start in: `C:\Project\anti-code\youtube-auto`

Thay đường dẫn bằng `youtube-stoicism` cho bot còn lại.

## 9. Chạy bằng Docker

Trong thư mục pipeline:

```powershell
docker compose build
docker compose up -d
docker compose logs -f
```

Container mặc định chạy `scheduler.py`. File `.env`, OAuth credentials, YouTube token, Facebook token và output được đọc qua volume hiện có. Thực hiện YouTube OAuth lần đầu bằng Python trên máy host trước khi chạy container vì container không thuận tiện mở trình duyệt.

## Tùy chỉnh

Các thiết lập nội dung và video nằm trong `config.py` của từng pipeline:

- `CHANNEL_NAME`, `BASE_TAGS`, `TARGET_RELIGION`.
- `TTS_VOICE`, `TTS_RATE`, `TTS_PITCH`.
- `YOUTUBE_PRIVACY`, `YOUTUBE_LANGUAGE`, `YOUTUBE_CATEGORY`.
- `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_GRAPH_API_VERSION`.
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
| Thiếu `FACEBOOK_PAGE_ID` hoặc token | Điền hai giá trị vào `youtube-auto/.env`, rồi chạy `python main.py --facebook-page`. |
| Facebook `code=190` | Page token hết hạn hoặc không hợp lệ; tạo token mới. |
| Facebook `code=200` | Token thiếu `pages_manage_posts` hoặc user không có quyền tạo nội dung trên Page. |
| Audio dài hơn 58 giây | Chạy lại để tạo script khác hoặc giảm giới hạn từ trong `script_gen.py`. |

Log lỗi provider bao gồm HTTP status và phần đầu response body, nhưng không ghi API key/token.

## Lưu ý vận hành

- Không chạy đồng thời hai instance của cùng một pipeline vì có thể trùng lịch sử topic hoặc output ID.
- Kiểm tra vài video đầu bằng `--dry-run` trước khi bật scheduler.
- Nội dung dùng template lặp lại có thể ảnh hưởng điều kiện kiếm tiền của YouTube; nên kiểm tra chất lượng và tính khác biệt trước khi public.
- Khai báo nội dung tổng hợp/AI trong YouTube Studio khi hình ảnh có vẻ chân thực và thuộc trường hợp YouTube yêu cầu disclosure.
