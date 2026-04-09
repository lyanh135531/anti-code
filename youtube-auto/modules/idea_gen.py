"""
==========================================================
  MODULE: IDEA GENERATOR — SHORTS CHỦ ĐỀ CHÚA JESUS
  Dùng Pollinations AI (không phải Gemini) — không bị 429!
==========================================================
"""

import logging
import os
from modules.pollinations_text import chat_complete, extract_json

logger = logging.getLogger(__name__)

HISTORY_FILE = ".topic_history.txt"


def _get_past_topics() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()][-50:]


def _save_topic_to_history(topic: str):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{topic}\n")


def generate_new_topic() -> dict:
    """
    Sáng tạo một chủ đề Shorts mới về Chúa Jesus và Kinh Thánh.
    Chủ đề PHẢI cụ thể, xúc động và trực tiếp liên quan đến Jesus Christ.
    """
    logger.info("Đang sáng tạo chủ đề Shorts về Chúa Jesus (Pollinations)...")

    past_topics = _get_past_topics()
    history_str = "\n".join([f"- {t}" for t in past_topics]) if past_topics else "None yet."

    system = (
        "You are a YouTube Shorts content strategist for a Christian channel called 'Spiritus' "
        "dedicated EXCLUSIVELY to Jesus Christ, the Bible, and Christian faith. "
        "Your job is to create emotionally powerful, faith-inspiring short video topics about JESUS CHRIST specifically."
    )

    prompt = f"""Generate ONE new YouTube Shorts topic about JESUS CHRIST for the Spiritus channel.

RECENTLY COVERED TOPICS (DO NOT duplicate):
{history_str}

STRICT REQUIREMENTS:
- The topic MUST specifically mention Jesus, Christ, God, the Bible, or a specific Bible event/verse.
- Do NOT create generic "spirituality", "wisdom", or "meditation" topics.
- Focus on: Jesus's miracles, His teachings, His love, His sacrifice, specific Bible stories, promises of God, His resurrection, answered prayers, His mercy and grace.
- The hook must create URGENCY and EMOTION — make viewers stop scrolling.

Return ONLY a valid JSON object:
{{
  "topic": "An emotionally powerful Shorts title about Jesus (max 60 chars, include Jesus or God or Bible)",
  "keywords": ["jesus", "bible", "faith", "christianity", "god"],
  "shorts_hook": "One explosive hook sentence to open the 50-second video (start with a Bible verse or shocking fact about Jesus)",
  "visual_theme": "One sentence describing the overall visual style (e.g. 'Ancient Jerusalem scenes with divine golden light')",
  "bible_reference": "One specific Bible verse (e.g. John 3:16)"
}}"""

    raw = chat_complete(prompt, system=system, temperature=0.9, json_mode=True)
    topic_config = extract_json(raw)

    required = ["topic", "keywords", "shorts_hook", "visual_theme", "bible_reference"]
    for key in required:
        if key not in topic_config:
            raise ValueError(f"Missing key in topic response: '{key}'")

    topic_config["religion"] = "Christianity"
    _save_topic_to_history(topic_config["topic"])
    logger.info(f"✅ Topic về Chúa Jesus: {topic_config['topic']}")
    return topic_config
