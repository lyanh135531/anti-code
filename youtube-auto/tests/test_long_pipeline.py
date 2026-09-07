from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import long_main
from config import LONG_MAX_DURATION, LONG_MAX_IMAGES, LONG_MIN_DURATION, LONG_MIN_IMAGES
from modules import long_script_gen
from modules.long_video_maker import _caption_cues
from modules.long_sources import fetch_source, is_allowed_source
from modules.long_topics import load_history, record_topic, select_topic


def source_pack():
    return {
        "bible_passage": "Luke 10:25-37",
        "sources": [
            {"id": "BIBLE", "url": "https://bible.usccb.org/bible/luke/10", "text": "Bible " * 200},
            {"id": "CCC_TOPIC_1", "url": "https://www.vatican.va/x", "text": "Catechism " * 200},
        ],
    }


def valid_script():
    counts = [4, 4, 4, 3, 3, 3, 3]
    sections = []
    for kind, count in zip(long_script_gen.REQUIRED_SECTION_KINDS, counts):
        sections.append(
            {
                "kind": kind,
                "heading": kind.replace("_", " ").title(),
                "narration": "faith " * 125,
                "source_refs": ["BIBLE", "CCC_TOPIC_1"],
                "on_screen_text": "Choose Mercy",
                "visual_prompts": [f"visual {kind} {index}" for index in range(count)],
            }
        )
    return {
        "title": "The Good Samaritan and the Neighbor We Avoid",
        "thumbnail_text": "Choose Your Neighbor",
        "bible_passage": "Luke 10:25-37",
        "summary": "A source-grounded reflection.",
        "sections": sections,
        "description": "A Catholic reflection on the Good Samaritan.",
        "tags": ["Catholic", "Bible"],
    }


class LongTopicTests(unittest.TestCase):
    def test_history_is_independent_and_selects_unused_topic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".long_topic_history.txt"
            first_id, _ = select_topic(path)
            record_topic(path, first_id)
            second_id, _ = select_topic(path)
            self.assertNotEqual(first_id, second_id)
            self.assertEqual(load_history(path), [first_id])

    def test_unknown_topic_is_rejected(self):
        with self.assertRaises(ValueError):
            select_topic("missing-history", "not-a-real-story")


class SourceTests(unittest.TestCase):
    def test_allowlist(self):
        self.assertTrue(is_allowed_source("https://bible.usccb.org/bible/luke/10"))
        self.assertTrue(is_allowed_source("https://www.vatican.va/content/test"))
        self.assertFalse(is_allowed_source("http://www.vatican.va/content/test"))
        self.assertFalse(is_allowed_source("https://example.com/vatican"))

    @patch("modules.long_sources.requests.get")
    def test_source_network_failure_is_not_silenced(self, get):
        get.side_effect = RuntimeError("offline")
        with self.assertRaises(RuntimeError):
            fetch_source("https://bible.usccb.org/bible/luke/10")


class ScriptTests(unittest.TestCase):
    def test_long_limits_match_free_quota_profile(self):
        self.assertEqual((LONG_MIN_DURATION, LONG_MAX_DURATION), (300, 420))
        self.assertEqual((LONG_MIN_IMAGES, LONG_MAX_IMAGES), (24, 28))

    def test_schema_derives_required_top_level_fields(self):
        script = long_script_gen.normalize_and_validate(valid_script(), source_pack())
        self.assertEqual(len(script["visual_prompts"]), 24)
        self.assertEqual(script["word_count"], 875)
        self.assertEqual(script["verification_status"], "PENDING")

    def test_long_burned_caption_is_at_most_two_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            srt = Path(directory) / "captions.srt"
            srt.write_text(
                "1\n00:00:00,000 --> 00:00:08,000\n"
                + "This deliberately long subtitle phrase must be split into compact readable chunks "
                + "instead of covering the central subject in the video frame.\n",
                encoding="utf-8",
            )
            cues = _caption_cues(srt)
            self.assertGreater(len(cues), 1)
            for _, _, text in cues:
                lines = text.splitlines()
                self.assertLessEqual(len(lines), 2)
                self.assertTrue(all(len(line) <= 42 for line in lines))

    def test_missing_citation_fails(self):
        script = valid_script()
        script["sections"][0]["source_refs"] = []
        with self.assertRaises(ValueError):
            long_script_gen.normalize_and_validate(script, source_pack())

    @patch("modules.long_script_gen.chat_complete")
    def test_verifier_rejects_empty_claim_list_even_if_model_says_pass(self, complete):
        complete.return_value = '{"status":"PASS","reason":"ok","claims":[],"required_changes":[]}'
        normalized = long_script_gen.normalize_and_validate(valid_script(), source_pack())
        report = long_script_gen.verify_script(normalized, source_pack())
        self.assertEqual(report["status"], "FAIL")

    @patch("modules.long_script_gen.chat_complete")
    def test_verifier_requires_and_accepts_all_seven_section_audits(self, complete):
        responses = []
        for kind in long_script_gen.REQUIRED_SECTION_KINDS:
            responses.append(
                '{"status":"PASS","reason":"supported","claims":['
                f'{{"section":"{kind}","claim":"No material claim",'
                '"source_refs":["BIBLE"],"status":"PASS","reason":"supported"}],'
                '"required_changes":[]}'
            )
        complete.side_effect = responses
        normalized = long_script_gen.normalize_and_validate(valid_script(), source_pack())
        report = long_script_gen.verify_script(normalized, source_pack())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(complete.call_count, 7)


class PipelineTests(unittest.TestCase):
    def test_schedule_stays_at_7pm_eastern_across_dst(self):
        eastern = ZoneInfo("America/New_York")
        winter = long_main.next_publish_time(datetime(2026, 1, 7, 12, tzinfo=eastern))
        summer = long_main.next_publish_time(datetime(2026, 7, 8, 12, tzinfo=eastern))
        self.assertEqual((winter.weekday(), winter.hour), (2, 19))
        self.assertEqual((summer.weekday(), summer.hour), (2, 19))
        self.assertNotEqual(winter.utcoffset(), summer.utcoffset())

    def test_accuracy_failure_blocks_tts_and_upload(self):
        normalized = long_script_gen.normalize_and_validate(valid_script(), source_pack())
        with tempfile.TemporaryDirectory() as directory, patch.object(
            long_main, "LONG_ROOT", Path(directory) / "output"
        ), patch.object(
            long_main, "LONG_HISTORY", Path(directory) / ".long_history"
        ), patch.object(
            long_main, "build_source_pack", return_value=source_pack()
        ), patch.object(
            long_main, "generate_research_brief", return_value={"narrative_facts": []}
        ), patch.object(
            long_main, "generate_long_script", return_value=normalized
        ), patch.object(
            long_main,
            "verify_with_one_repair",
            return_value=(normalized, {"status": "FAIL", "required_changes": ["bad claim"]}),
        ), patch.object(long_main, "text_to_speech") as tts, patch.object(
            long_main, "upload_video"
        ) as upload:
            result = long_main.run_long_pipeline(topic_id="good-samaritan")
            self.assertFalse(result["success"])
            self.assertEqual(result["verification_status"], "FAIL")
            tts.assert_not_called()
            upload.assert_not_called()

    def test_shorts_entrypoint_still_imports(self):
        import main

        self.assertTrue(callable(main.run_pipeline))


if __name__ == "__main__":
    unittest.main()
