"""
==========================================================
  MODULE: IDEA GENERATOR (NEW SDK)
  Dùng Google Gemini API (google-genai) để tự động sáng tạo chủ đề
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
    return [line.strip() for line in lines if line.strip()][-50:]  # Lấy 50 bài gần nhất


def _save_topic_to_history(topic: str):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{topic}\n")


def generate_new_topic(target_religion: str = "Christianity") -> dict:
    """
    Sáng tạo một chủ đề hoàn toàn mới chưa từng làm.
    Tự động thử nhiều model fallback nếu model chính hết quota.
    """
    logger.info("Đang sáng tạo chủ đề mới...")
    client = _get_client()
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

    # Danh sách model theo thứ tự ưu tiên
    model_list = [GEMINI_MAIN_MODEL] + GEMINI_FALLBACK_MODELS
    last_error = None

    for model_id in model_list:
        logger.info(f"Thử tạo ý tưởng với model: {model_id}")
        for attempt in range(2):  # 2 lần thử mỗi model
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
                
                # Dọn dấu markdown nếu có
                raw = re.sub(r'^```json\s*', '', raw)
                raw = re.sub(r'^```\s*', '', raw)
                raw = re.sub(r'```$', '', raw).strip()

                # Tìm JSON object trong text
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    raw = json_match.group()

                # Parse JSON
                topic_config = json.loads(raw)

                # Validate essential keys
                for key in ["topic", "religion", "keywords", "script_angle", "shorts_hook"]:
                    if key not in topic_config:
                        raise ValueError(f"Thiếu key '{key}' trong JSON trả về")

                _save_topic_to_history(topic_config["topic"])
                logger.info(f"Đã lên ý tưởng thành công ({model_id}): {topic_config['topic']}")
                return topic_config

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Lần {attempt+1}/2 thất bại ({model_id}): {err_str[:200]}")

                is_quota_error = "429" in err_str or "quota" in err_str or "exhausted" in err_str
                is_overload_error = "503" in err_str or "unavailable" in err_str

                if is_quota_error:
                    # Quota hết → chuyển ngay sang model tiếp theo, không retry
                    logger.info(f"Hết quota model {model_id} → chuyển model...")
                    break  # Thoát vòng attempt, sang model tiếp theo
                elif is_overload_error:
                    logger.info("Server quá tải, chờ 10s...")
                    time.sleep(10)
                else:
                    time.sleep(5)

        logger.info(f"Thử model tiếp theo...")

    raise RuntimeError(
        f"Không thể sáng tạo chủ đề sau khi thử tất cả {len(model_list)} model. "
        f"Lỗi cuối: {last_error}"
    )
