from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import main


def scenes():
    return [{"image_prompt": f"scene {index}"} for index in range(9)]


class ShortsPublishingTests(unittest.TestCase):
    def _pipeline_patches(self, directory):
        root = Path(directory)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        return [
            patch.object(main, "OUTPUT_DIR", root / "output"),
            patch.object(main, "LOG_DIR", root / "logs"),
            patch.object(main, "_generate_video_id", return_value="sh_test"),
            patch.object(
                main,
                "generate_new_topic",
                return_value={"topic": "Faith", "bible_reference": "Luke 1"},
            ),
            patch.object(
                main,
                "generate_shorts_script",
                return_value={
                    "scenes": scenes(),
                    "clean_script": "Narration",
                    "script": "Narration",
                    "word_count": 1,
                    "bible_reference": "Luke 1",
                },
            ),
            patch.object(main, "save_script"),
            patch.object(
                main,
                "generate_seo_metadata",
                return_value={
                    "title": "Title",
                    "shorts_title": "Short title",
                    "shorts_description": "Description",
                    "description": "Description",
                    "tags": ["faith"],
                },
            ),
            patch.object(main, "format_description_for_youtube", side_effect=lambda x: x),
            patch.object(main, "text_to_speech"),
            patch.object(main, "get_audio_duration", return_value=30),
            patch.object(main, "generate_shorts_images", return_value=["image.png"] * 9),
            patch.object(main, "create_shorts_from_images", return_value="video.mp4"),
            patch.object(main, "_get_background_music", return_value=None),
        ]

    def test_platform_failures_are_independent_and_fail_run(self):
        with tempfile.TemporaryDirectory() as directory:
            patches = self._pipeline_patches(directory)
            for item in patches:
                item.start()
                self.addCleanup(item.stop)
            with patch.object(main, "upload_shorts", side_effect=RuntimeError("quota")) as youtube, patch.object(
                main, "upload_facebook_reel", return_value="fb-123"
            ) as facebook:
                result = main.run_pipeline(platforms=("youtube", "facebook"))

        youtube.assert_called_once()
        facebook.assert_called_once()
        self.assertFalse(result["success"])
        self.assertEqual(result["facebook_reel_id"], "fb-123")
        self.assertTrue(any(error.startswith("YouTube:") for error in result["errors"]))

    def test_dry_run_calls_no_uploader(self):
        with tempfile.TemporaryDirectory() as directory:
            patches = self._pipeline_patches(directory)
            for item in patches:
                item.start()
                self.addCleanup(item.stop)
            with patch.object(main, "upload_shorts") as youtube, patch.object(
                main, "upload_facebook_reel"
            ) as facebook:
                result = main.run_pipeline(
                    upload=False,
                    dry_run=True,
                    platforms=("youtube", "facebook"),
                )

        self.assertTrue(result["success"])
        youtube.assert_not_called()
        facebook.assert_not_called()

    def test_schedule_under_ten_minutes_rolls_to_next_day(self):
        tz = timezone(timedelta(hours=7))
        now = datetime(2026, 9, 4, 18, 55, tzinfo=tz)
        publish_at = main._next_publish_at(19, now)
        self.assertEqual(publish_at, datetime(2026, 9, 5, 19, 0, tzinfo=tz))


if __name__ == "__main__":
    unittest.main()
