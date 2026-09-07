from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from modules import facebook_uploader


def response(payload, status_code=200):
    item = Mock()
    item.ok = 200 <= status_code < 300
    item.status_code = status_code
    item.json.return_value = payload
    return item


class FacebookUploaderTests(unittest.TestCase):
    def setUp(self):
        self.credentials = patch.multiple(
            facebook_uploader,
            FACEBOOK_PAGE_ID="page-123",
            FACEBOOK_PAGE_ACCESS_TOKEN="secret-token",
            FACEBOOK_GRAPH_API_VERSION="v26.0",
        )
        self.credentials.start()
        self.addCleanup(self.credentials.stop)

    def _video(self, directory):
        path = Path(directory) / "reel.mp4"
        path.write_bytes(b"video-bytes")
        return path

    def _session(self):
        session = Mock()
        session.post.side_effect = [
            response(
                {
                    "video_id": "video-456",
                    "upload_url": "https://rupload.facebook.com/video-upload/v26.0/video-456",
                }
            ),
            response({"success": True}),
            response({"success": True}),
        ]
        session.get.return_value = response(
            {"status": {"uploading_phase": {"status": "complete"}}}
        )
        return session

    def test_immediate_upload_uses_start_upload_status_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            session = self._session()
            with patch.object(facebook_uploader.requests, "Session", return_value=session):
                video_id = facebook_uploader.upload_facebook_reel(
                    self._video(directory), "Title", "Description"
                )

        self.assertEqual(video_id, "video-456")
        self.assertEqual(session.post.call_count, 3)
        start_call, upload_call, finish_call = session.post.call_args_list
        self.assertEqual(start_call.kwargs["data"], {"upload_phase": "start"})
        self.assertEqual(upload_call.kwargs["headers"]["file_size"], "11")
        self.assertEqual(upload_call.kwargs["headers"]["offset"], "0")
        self.assertEqual(finish_call.kwargs["data"]["video_state"], "PUBLISHED")
        self.assertNotIn("scheduled_publish_time", finish_call.kwargs["data"])
        self.assertNotIn("secret-token", start_call.args[0])

    def test_scheduled_upload_sends_unix_timestamp(self):
        publish_at = datetime.now(timezone.utc) + timedelta(hours=2)
        with tempfile.TemporaryDirectory() as directory:
            session = self._session()
            with patch.object(facebook_uploader.requests, "Session", return_value=session):
                facebook_uploader.upload_facebook_reel(
                    self._video(directory), "Title", "Description", publish_at
                )

        finish_data = session.post.call_args_list[2].kwargs["data"]
        self.assertEqual(finish_data["video_state"], "SCHEDULED")
        self.assertEqual(finish_data["scheduled_publish_time"], int(publish_at.timestamp()))

    def test_missing_credentials_fails_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            facebook_uploader, "FACEBOOK_PAGE_ID", ""
        ), patch.object(facebook_uploader.requests, "Session") as session:
            with self.assertRaisesRegex(
                facebook_uploader.FacebookUploadError, "FACEBOOK_PAGE_ID"
            ):
                facebook_uploader.upload_facebook_reel(
                    self._video(directory), "Title", "Description"
                )
            session.assert_not_called()

    def test_missing_file_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            facebook_uploader.upload_facebook_reel(
                "missing.mp4", "Title", "Description"
            )

    def test_graph_error_does_not_expose_token(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Mock()
            session.post.return_value = response(
                {"error": {"code": 190, "message": "Bad secret-token"}}, 400
            )
            with patch.object(facebook_uploader.requests, "Session", return_value=session):
                with self.assertRaises(facebook_uploader.FacebookUploadError) as caught:
                    facebook_uploader.upload_facebook_reel(
                        self._video(directory), "Title", "Description"
                    )
        self.assertNotIn("secret-token", str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))

    def test_timeout_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Mock()
            session.post.side_effect = requests.Timeout("timeout")
            with patch.object(facebook_uploader.requests, "Session", return_value=session):
                with self.assertRaisesRegex(
                    facebook_uploader.FacebookUploadError, "không tự retry"
                ):
                    facebook_uploader.upload_facebook_reel(
                        self._video(directory), "Title", "Description"
                    )
        self.assertEqual(session.post.call_count, 1)

    def test_page_info_check_uses_header_not_query_token(self):
        session = Mock()
        session.get.return_value = response({"id": "page-123", "name": "Spiritus"})
        with patch.object(facebook_uploader.requests, "Session", return_value=session):
            page = facebook_uploader.get_facebook_page_info()

        self.assertEqual(page, {"id": "page-123", "name": "Spiritus"})
        call = session.get.call_args
        self.assertEqual(call.kwargs["params"], {"fields": "id,name"})
        self.assertNotIn("secret-token", call.args[0])
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer secret-token")

    def test_failed_processing_status_blocks_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            session = self._session()
            session.get.return_value = response(
                {"status": {"video_status": "error"}}
            )
            with patch.object(facebook_uploader.requests, "Session", return_value=session):
                with self.assertRaisesRegex(
                    facebook_uploader.FacebookUploadError, "xử lý Reel thất bại"
                ):
                    facebook_uploader.upload_facebook_reel(
                        self._video(directory), "Title", "Description"
                    )
        self.assertEqual(session.post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
