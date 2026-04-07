"""
==========================================================
  MODULE: IDEA GENERATOR
  Dùng Google Gemini API để tự động sáng tạo chủ đề
==========================================================
"""

import logging
import time
import re
import json
import os
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

HISTORY_FILE = ".topic_history.txt"

def _configure_gemini():
    """Cấu hình Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-3-flash-preview")

def _get_past_topics() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()][-50:] # Lấy 50 bài gần nhất

def _save_topic_to_history(topic: str):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{topic}\n")

def generate_new_topic(target_religion: str = "Christianity") -> dict:
    """
    Sáng tạo một chủ đề hoàn toàn mới chưa từng làm.
    """
    logger.info("Đang sáng tạo chủ đề mới...")
    model = _configure_gemini()
    past_topics = _get_past_topics()
    
    history_str = "\n".join([f"- {t}" for t in past_topics]) if past_topics else "Chưa có video nào."

    prompt = f"""You are an expert YouTube content strategist for a channel dedicated to {target_religion}.

Here are the recent topics we already covered. Do NOT duplicate them:
{history_str}

Generate ONE new highly engaging YouTube video topic.
Return ONLY a valid JSON object with these keys:
- "topic": The catchy YouTube title (max 60 chars)
- "religion": "{target_religion}"
- "keywords": list of 5 search keywords (e.g. ["bible", "faith", "miracles", "god", "history"])
- "script_angle": 1 sentence describing the perspective/narrative flow of the 5-minute video.
- "shorts_hook": A clickbaity 1-sentence hook for a 60-second YouTube shorts version.

Do NOT include markdown like ```json. Return raw valid JSON.
"""

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,
                    max_output_tokens=800,
                )
            )
            
            raw = response.text.strip()
            # Xóa các markdown block
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                raw = json_match.group()
            
            topic_config = json.loads(raw, strict=False)
            
            # Validate essential keys
            for key in ["topic", "religion", "keywords", "script_angle", "shorts_hook"]:
                if key not in topic_config:
                    raise ValueError(f"Thiếu key {key} trong JSON trả về")
            
            _save_topic_to_history(topic_config["topic"])
            logger.info(f"Đã lên ý tưởng thành công: {topic_config['topic']}")
            return topic_config

        except Exception as e:
            err_str = str(e)
            logger.warning(f"Sáng tạo ý tưởng lần {attempt+1}/3 thất bại: {err_str}")
            if attempt < 2:
                if "429" in err_str or "quota" in err_str.lower() or "retry in" in err_str.lower():
                    logger.info("⏳ Quá tải Gemini API (Rate Limit), tạm dừng 45s trước khi thử lại...")
                    time.sleep(45)
                else:
                    time.sleep(5)

    raise RuntimeError("Không thể sáng tạo chủ đề sau 3 lần thử.")
