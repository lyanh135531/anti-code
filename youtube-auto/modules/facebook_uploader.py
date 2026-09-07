"""Upload local vertical videos to a Facebook Page as Reels."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from config import (
    FACEBOOK_GRAPH_API_VERSION,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    FACEBOOK_PAGE_ID,
)

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"
REQUEST_TIMEOUT = (15, 120)
UPLOAD_TIMEOUT = (15, 900)
STATUS_ATTEMPTS = 10
STATUS_DELAY_SECONDS = 2


class FacebookUploadError(RuntimeError):
    """Raised when Meta rejects or cannot complete a Reel upload."""


def _credentials() -> tuple[str, str, str]:
    page_id = FACEBOOK_PAGE_ID.strip()
    token = FACEBOOK_PAGE_ACCESS_TOKEN.strip()
    version = FACEBOOK_GRAPH_API_VERSION.strip()
    if not page_id or not token:
        raise FacebookUploadError(
            "Thiếu FACEBOOK_PAGE_ID hoặc FACEBOOK_PAGE_ACCESS_TOKEN trong .env"
        )
    if not version:
        raise FacebookUploadError("Thiếu FACEBOOK_GRAPH_API_VERSION trong .env")
    if not version.startswith("v"):
        version = f"v{version}"
    return page_id, token, version


def _auth_headers(token: str, *, upload: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"OAuth {token}" if upload else f"Bearer {token}"}
    if upload:
        headers["Content-Type"] = "application/octet-stream"
    return headers


def _safe_error(response: requests.Response, token: str, action: str) -> FacebookUploadError:
    message = ""
    code: Any = None
    subcode: Any = None
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = str(error.get("message", ""))
        code = error.get("code")
        subcode = error.get("error_subcode")
    except (ValueError, TypeError):
        pass
    if token:
        message = message.replace(token, "[REDACTED]")
    details = [f"HTTP {response.status_code}"]
    if code is not None:
        details.append(f"code={code}")
    if subcode is not None:
        details.append(f"subcode={subcode}")
    if message:
        details.append(message[:500])
    return FacebookUploadError(f"Facebook {action} thất bại: {'; '.join(details)}")


def _json_response(
    response: requests.Response,
    token: str,
    action: str,
) -> dict[str, Any]:
    if not response.ok:
        raise _safe_error(response, token, action)
    try:
        payload = response.json()
    except ValueError as error:
        raise FacebookUploadError(
            f"Facebook {action} trả về dữ liệu không phải JSON"
        ) from error
    if not isinstance(payload, dict):
        raise FacebookUploadError(f"Facebook {action} trả về dữ liệu không hợp lệ")
    return payload


def _get_status(
    session: requests.Session,
    video_id: str,
    token: str,
    version: str,
) -> dict[str, Any]:
    url = f"{GRAPH_BASE}/{version}/{video_id}"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = session.get(
                url,
                params={"fields": "status"},
                headers=_auth_headers(token),
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = _safe_error(response, token, "kiểm tra trạng thái")
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
            return _json_response(response, token, "kiểm tra trạng thái")
        except requests.RequestException as error:
            last_error = error
            if attempt < 2:
                time.sleep(2**attempt)
                continue
    raise FacebookUploadError(
        f"Không kiểm tra được trạng thái Facebook: {type(last_error).__name__}"
    ) from last_error


def _wait_for_upload(
    session: requests.Session,
    video_id: str,
    token: str,
    version: str,
) -> None:
    for attempt in range(STATUS_ATTEMPTS):
        payload = _get_status(session, video_id, token, version)
        status = payload.get("status", {})
        if not isinstance(status, dict):
            status = {}
        phases = [
            status.get("uploading_phase", {}),
            status.get("processing_phase", {}),
            status.get("publishing_phase", {}),
        ]
        phase_states = {
            str(phase.get("status", "")).lower()
            for phase in phases
            if isinstance(phase, dict)
        }
        video_status = str(status.get("video_status", "")).lower()
        if video_status in {"error", "failed"} or phase_states & {"error", "failed"}:
            raise FacebookUploadError(
                f"Facebook xử lý Reel thất bại (video_status={video_status or 'unknown'})"
            )
        uploading = status.get("uploading_phase", {})
        if (
            isinstance(uploading, dict)
            and str(uploading.get("status", "")).lower() == "complete"
        ):
            return
        if attempt < STATUS_ATTEMPTS - 1:
            time.sleep(STATUS_DELAY_SECONDS)
    raise FacebookUploadError("Facebook không xác nhận upload hoàn tất trong thời gian chờ")


def _scheduled_timestamp(publish_at: datetime | int | float | None) -> int | None:
    if publish_at is None:
        return None
    if isinstance(publish_at, datetime):
        if publish_at.tzinfo is None:
            raise ValueError("publish_at phải có timezone")
        timestamp = int(publish_at.timestamp())
    else:
        timestamp = int(publish_at)
    if timestamp < int(datetime.now(timezone.utc).timestamp()) + 600:
        raise ValueError("Facebook yêu cầu lịch đăng cách hiện tại ít nhất 10 phút")
    return timestamp


def upload_facebook_reel(
    video_path: str | Path,
    title: str,
    description: str,
    publish_at: datetime | int | float | None = None,
) -> str:
    """Upload a local MP4 and publish or schedule it as a Facebook Page Reel."""
    path = Path(video_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"File video không tồn tại hoặc rỗng: {path}")

    page_id, token, version = _credentials()
    scheduled_at = _scheduled_timestamp(publish_at)
    endpoint = f"{GRAPH_BASE}/{version}/{page_id}/video_reels"
    session = requests.Session()

    try:
        # Deliberately do not retry mutating calls: a lost response can mean the
        # server accepted the operation, and retrying can create duplicate Reels.
        start_response = session.post(
            endpoint,
            data={"upload_phase": "start"},
            headers=_auth_headers(token),
            timeout=REQUEST_TIMEOUT,
        )
        start = _json_response(start_response, token, "tạo phiên upload")
        video_id = str(start.get("video_id", "")).strip()
        upload_url = str(start.get("upload_url", "")).strip()
        if not video_id or not upload_url:
            raise FacebookUploadError("Facebook không trả về video_id/upload_url")
        if urlparse(upload_url).hostname != "rupload.facebook.com":
            raise FacebookUploadError("Facebook trả về upload_url không hợp lệ")

        file_size = path.stat().st_size
        upload_headers = _auth_headers(token, upload=True)
        upload_headers.update({"offset": "0", "file_size": str(file_size)})
        with path.open("rb") as video_file:
            upload_response = session.post(
                upload_url,
                data=video_file,
                headers=upload_headers,
                timeout=UPLOAD_TIMEOUT,
            )
        upload_result = _json_response(upload_response, token, "upload file")
        if upload_result.get("success") is not True:
            raise FacebookUploadError("Facebook không xác nhận đã nhận file video")

        _wait_for_upload(session, video_id, token, version)

        finish_data: dict[str, Any] = {
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "SCHEDULED" if scheduled_at else "PUBLISHED",
            "title": title,
            "description": description,
        }
        if scheduled_at:
            finish_data["scheduled_publish_time"] = scheduled_at
        finish_response = session.post(
            endpoint,
            data=finish_data,
            headers=_auth_headers(token),
            timeout=REQUEST_TIMEOUT,
        )
        finish = _json_response(finish_response, token, "xuất bản Reel")
        if finish.get("success") is not True:
            raise FacebookUploadError("Facebook không xác nhận đã xuất bản Reel")
        logger.info("Facebook Reel accepted: %s", video_id)
        return video_id
    except requests.RequestException as error:
        raise FacebookUploadError(
            f"Lỗi kết nối Facebook ({type(error).__name__}); không tự retry để tránh đăng trùng"
        ) from error
    finally:
        session.close()


def get_facebook_page_info() -> dict[str, Any]:
    """Validate configured credentials and return basic Page information."""
    page_id, token, version = _credentials()
    session = requests.Session()
    try:
        response = session.get(
            f"{GRAPH_BASE}/{version}/{page_id}",
            params={"fields": "id,name"},
            headers=_auth_headers(token),
            timeout=REQUEST_TIMEOUT,
        )
        payload = _json_response(response, token, "đọc thông tin Page")
        return {"id": payload.get("id", ""), "name": payload.get("name", "")}
    except requests.RequestException as error:
        raise FacebookUploadError(
            f"Lỗi kết nối Facebook ({type(error).__name__})"
        ) from error
    finally:
        session.close()
