"""
==========================================================
  MODULE: IDEA GENERATOR — SHORTS CHỦ ĐỀ CHÚA JESUS
  Tạo chủ đề YouTube Shorts tập trung hoàn toàn về Jesus,
  Kinh Thánh, Đức Tin Kitô Giáo và Lời Chúa.
==========================================================
"""

import logging
import time
import re
import json
import os
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MAIN_MODEL, GEMINI_FALLBACK_MODELS

logger = logging.getLogger(__name__)

HISTORY_FILE = ".topic_history.txt"


def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


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
    logger.info("Đang sáng tạo chủ đề Shorts về Chúa Jesus...")
    client = _get_client()
    past_topics = _get_past_topics()

    history_str = "\n".join([f"- {t}" for t in past_topics]) if past_topics else "None yet."

    prompt = f"""You are a YouTube Shorts content strategist for a Christian channel called "Spiritus" dedicated EXCLUSIVELY to Jesus Christ, the Bible, and Christian faith.

The channel's mission: Share the love, power, and teachings of JESUS CHRIST to inspire and strengthen faith worldwide.

RECENTLY COVERED TOPICS (DO NOT duplicate):
{history_str}

Generate ONE new, highly emotional and faith-inspiring YouTube Shorts topic about JESUS CHRIST.

STRICT REQUIREMENTS:
- The topic MUST specifically mention Jesus, Christ, God, the Bible, a specific Bible verse, or a specific event from Jesus's life.
- Do NOT create generic "spirituality", "wisdom", or "meditation" topics.
- Focus on: Jesus's miracles, His teachings, His love, His sacrifice, specific Bible stories, promises of God, His resurrection, answered prayers, His mercy and grace.
- The hook must create URGENCY and EMOTION — make viewers stop scrolling.

Return ONLY a valid JSON object with these exact keys:
{{
  "topic": "An emotionally powerful, specific Shorts title about Jesus (max 60 chars, include Jesus or God or Bible)",
  "keywords": ["jesus", "bible", "faith", "christianity", "god"],
  "shorts_hook": "One explosive hook sentence to open the 50-second video (start with a Bible verse reference or a shocking fact about Jesus)",
  "visual_theme": "One sentence describing the overall visual style (e.g. 'Ancient Jerusalem scenes with divine golden light')",
  "bible_reference": "One specific Bible verse to anchor the content (e.g. John 3:16)"
}}

Do NOT include markdown. Return raw JSON only."""

    model_list = [GEMINI_MAIN_MODEL] + GEMINI_FALLBACK_MODELS
    last_error = None

    for model_id in model_list:
        logger.info(f"Thử tạo ý tưởng với model: {model_id}")
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.9,
                        max_output_tokens=1500,
                    )
                )

                raw = response.text.strip()

                # Clean markdown fences
                raw = re.sub(r'^```json\s*', '', raw)
                raw = re.sub(r'^```\s*', '', raw)
                raw = re.sub(r'```$', '', raw).strip()

                # Extract JSON object
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    raw = json_match.group()

                topic_config = json.loads(raw)

                # Validate required keys
                required = ["topic", "keywords", "shorts_hook", "visual_theme", "bible_reference"]
                for key in required:
                    if key not in topic_config:
                        raise ValueError(f"Missing key: '{key}'")

                # Inject fixed fields
                topic_config["religion"] = "Christianity"

                _save_topic_to_history(topic_config["topic"])
                logger.info(f"✅ Topic mới ({model_id}): {topic_config['topic']}")
                return topic_config

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Lần {attempt+1}/2 thất bại ({model_id}): {err_str[:200]}")

                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    logger.info(f"Hết quota {model_id} → chuyển model...")
                    break
                elif "503" in err_str or "unavailable" in err_str:
                    logger.info("Server quá tải, chờ 10s...")
                    time.sleep(10)
                else:
                    time.sleep(5)

        logger.info("Thử model tiếp theo...")

    raise RuntimeError(
        f"Không thể tạo topic sau khi thử tất cả model. Lỗi cuối: {last_error}"
    )
