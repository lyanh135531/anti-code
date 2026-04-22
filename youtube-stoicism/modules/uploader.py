"""
==========================================================
  MODULE: YOUTUBE UPLOADER
  Upload video lên YouTube bằng YouTube Data API v3 (miễn phí)
  
  LẦN ĐẦU CHẠY: Sẽ mở trình duyệt để xác thực Google
  Sau đó token được lưu lại → không cần xác thực lại
==========================================================
"""

import os
import time
import logging
import json
import pickle
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Scope cần thiết để upload YouTube
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

TOKEN_FILE = Path(__file__).parent.parent / "youtube_token.pickle"


# ============================================================
# XÁC THỰC OAUTH2
# ============================================================

def authenticate_youtube():
    """
    Xác thực với YouTube API qua OAuth2.
    - Lần đầu: Mở trình duyệt, bạn đăng nhập Google
    - Lần sau: Dùng token đã lưu tự động
    
    Returns:
        YouTube API service object
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    # ── Hỗ trợ GitHub Actions: Decode token từ Secrets ────────
    token_b64 = os.getenv("YOUTUBE_TOKEN_BASE64")
    if token_b64 and not TOKEN_FILE.exists():
        import base64
        try:
            with open(TOKEN_FILE, "wb") as f:
                f.write(base64.b64decode(token_b64))
            logger.info("Đã khôi phục YouTube token từ biến môi trường (Base64)")
        except Exception as e:
            logger.error(f"Lỗi giải mã YOUTUBE_TOKEN_BASE64: {e}")

    # Load token đã lưu
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        logger.info("Đã load YouTube token từ file")

    # Nếu token hết hạn, refresh tự động
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("YouTube token đã được refresh")
        except Exception as e:
            logger.warning(f"Không thể refresh token: {e} — sẽ xác thực lại")
            creds = None

    # Nếu chưa có token, mở trình duyệt xác thực
    if not creds or not creds.valid:
        client_secrets = Path(__file__).parent.parent / "client_secrets.json"
        if not client_secrets.exists():
            raise FileNotFoundError(
                f"Không tìm thấy 'client_secrets.json'!\n"
                f"Hãy tải file này từ Google Cloud Console theo hướng dẫn trong README."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets),
            scopes=YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(
            port=8080,
            prompt="consent",
            open_browser=True,
            success_message="✅ Xác thực thành công! Bạn có thể đóng cửa sổ này."
        )
        # Lưu token
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        logger.info(f"Token đã lưu: {TOKEN_FILE}")

    service = build("youtube", "v3", credentials=creds)
    return service


# ============================================================
# UPLOAD VIDEO CHÍNH
# ============================================================

def upload_video(
    video_path:    str | Path,
    thumbnail_path:str | Path,
    title:         str,
    description:   str,
    tags:          list[str],
    category_id:   str  = "27",
    language:      str  = "en",
    privacy:       str  = "public",
    publish_at:    str  = None,       # ISO 8601: "2026-04-07T18:00:00+07:00"
    made_for_kids: bool = False,
) -> Optional[str]:
    """
    Upload video lên YouTube.
    
    Args:
        video_path:     Đường dẫn file video MP4
        thumbnail_path: Đường dẫn file thumbnail JPG
        title:          Tiêu đề video (max 100 chars)
        description:    Mô tả video (max 5000 chars)
        tags:           Danh sách tags
        category_id:    ID category YouTube (27=Education)
        language:       Ngôn ngữ video
        privacy:        "public", "private", "unlisted"
        publish_at:     Thời điểm đăng (None = đăng ngay)
        made_for_kids:  Video cho trẻ em?
        
    Returns:
        Video ID nếu thành công, None nếu lỗi
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    # Validate
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"File video không tồn tại: {video_path}")

    # Truncate title & description nếu cần
    title       = title[:100]
    description = description[:5000]
    tags        = [t[:30] for t in tags[:500]]  # Max 500 tags, mỗi tag max 30 chars

    logger.info(f"Đang upload: '{title}' ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Body của request
    body = {
        "snippet": {
            "title":               title,
            "description":         description,
            "tags":                tags,
            "categoryId":          category_id,
            "defaultLanguage":     language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus":  privacy if not publish_at else "private",
            "madeForKids":    made_for_kids,
            "selfDeclaredMadeForKids": made_for_kids,
        }
    }

    # Nếu lên lịch đăng bài
    if publish_at:
        body["status"]["publishAt"]     = publish_at
        body["status"]["privacyStatus"] = "private"  # Phải là private để schedule

    # Xác thực
    service = authenticate_youtube()

    # Upload video với resumable upload (an toàn với file lớn)
    media = MediaFileUpload(
        str(video_path),
        mimetype    = "video/mp4",
        resumable   = True,
        chunksize   = 256 * 1024,  # 256 KB chunks
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    video_id = None
    retries = 0

    while video_id is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"  Upload progress: {progress}%")
            if response:
                video_id = response["id"]
                logger.info(f"✅ Upload xong! Video ID: {video_id}")

        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504] and retries < 5:
                wait = 2 ** retries
                logger.warning(f"Server lỗi {e.resp.status}, thử lại sau {wait}s...")
                time.sleep(wait)
                retries += 1
            else:
                logger.error(f"Upload thất bại: {e}")
                return None
        except Exception as e:
            logger.error(f"Upload lỗi không xác định: {e}")
            return None

    # Upload thumbnail
    if video_id and thumbnail_path and Path(thumbnail_path).exists():
        _upload_thumbnail(service, video_id, str(thumbnail_path))

    return video_id


def _upload_thumbnail(service, video_id: str, thumb_path: str):
    """Upload thumbnail cho video."""
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    try:
        media = MediaFileUpload(thumb_path, mimetype="image/jpeg")
        service.thumbnails().set(
            videoId    = video_id,
            media_body = media
        ).execute()
        logger.info(f"✅ Thumbnail đã upload cho video {video_id}")
    except HttpError as e:
        # YouTube yêu cầu kênh có ít nhất 1000 subscribers để set custom thumbnail
        logger.warning(
            f"Không thể upload thumbnail (cần 1000+ subscribers): {e.resp.status}"
        )
    except Exception as e:
        logger.warning(f"Thumbnail upload lỗi: {e}")


# ============================================================
# UPLOAD SHORTS
# ============================================================

def upload_shorts(
    video_path:    str | Path,
    title:         str,
    description:   str,
    tags:          list[str],
    privacy:       str  = "public",
    publish_at:    str  = None,
) -> Optional[str]:
    """
    Upload YouTube Shorts.
    Shorts được YouTube nhận diện tự động nếu video < 60s và 9:16 format.
    """
    # Thêm #Shorts vào title và description nếu chưa có
    if "#Shorts" not in title and "#shorts" not in title:
        title = (title[:90] + " #Shorts")[:100]
    
    # Thêm #Shorts vào đầu description
    shorts_desc = f"#Shorts\n\n{description}"
    
    logger.info("Uploading Shorts...")
    return upload_video(
        video_path     = video_path,
        thumbnail_path = None,    # Shorts không cần thumbnail
        title          = title,
        description    = shorts_desc[:5000],
        tags           = tags + ["shorts", "youtubeshorts"],
        privacy        = privacy,
        publish_at     = publish_at,
        made_for_kids  = False,
    )


# ============================================================
# LẤY THÔNG TIN KÊNH (để verify)
# ============================================================

def get_channel_info() -> dict:
    """Lấy thông tin kênh YouTube hiện tại."""
    service = authenticate_youtube()
    response = service.channels().list(
        part="snippet,statistics",
        mine=True
    ).execute()
    
    if response.get("items"):
        ch = response["items"][0]
        return {
            "id":           ch["id"],
            "name":         ch["snippet"]["title"],
            "subscribers":  ch["statistics"].get("subscriberCount", 0),
            "total_videos": ch["statistics"].get("videoCount", 0),
            "total_views":  ch["statistics"].get("viewCount", 0),
        }
    return {}
