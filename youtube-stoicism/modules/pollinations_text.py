"""
==========================================================
  MODULE: POLLINATIONS TEXT CLIENT
  Client chung cho tất cả text generation bằng Pollinations AI.
  Thay thế hoàn toàn Gemini API — không bao giờ bị 429 quota nữa.

  Base URL : https://gen.pollinations.ai
  Docs     : https://gen.pollinations.ai/api/docs
  API Key  : https://enter.pollinations.ai

  Models miễn phí (không tốn Pollen):
    - "openai"   : GPT-5 Mini — Nhanh & cân bằng
    - "openai-fast": GPT-5 Nano — Cực nhanh
    - "mistral"  : Mistral 24B — Tiết kiệm & hiệu quả
    - "deepseek" : DeepSeek V3 — Reasoning tốt
    - "claude-fast": Claude Haiku 4.5
==========================================================
"""

import logging
import time
import json
import re
import requests
from config import POLLINATIONS_API_KEY

logger = logging.getLogger(__name__)

# Endpoint
BASE_URL = "https://gen.pollinations.ai"

# Thứ tự model ưu tiên (miễn phí, không tốn Pollen)
DEFAULT_TEXT_MODELS = [
    "mistral",       # Mistral 24B — nhanh và ổn định nhất
    "openai",        # GPT-5 Mini — fallback 1
    "deepseek",      # DeepSeek V3 — fallback 2
    "claude-fast",   # Claude Haiku — fallback 3
    "openai-fast",   # GPT-5 Nano — fallback 4
]


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json",
    }


def chat_complete(
    prompt: str,
    system: str = None,
    model: str = None,
    temperature: float = 0.8,
    json_mode: bool = False,
    max_retries: int = 3,
) -> str:
    """
    Gọi Pollinations Chat Completions API.
    Tự động thử các model fallback nếu model hiện tại thất bại.

    Args:
        prompt      : Nội dung yêu cầu của người dùng
        system      : System prompt (optional)
        model       : Model cụ thể, None = tự chọn theo DEFAULT_TEXT_MODELS
        temperature : Độ sáng tạo (0.0–1.0)
        json_mode   : True = yêu cầu output JSON thuần

    Returns:
        Chuỗi kết quả (text hoặc JSON string)
    """
    models_to_try = [model] if model else DEFAULT_TEXT_MODELS
    url = f"{BASE_URL}/v1/chat/completions"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for model_id in models_to_try:
        for attempt in range(max_retries):
            try:
                payload = {
                    "model":       model_id,
                    "messages":    messages,
                    "temperature": temperature,
                    "seed":        -1,  # random mỗi lần
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = requests.post(
                    url,
                    headers=_get_headers(),
                    json=payload,
                    timeout=120,   # Script generation có thể mất tới 90s
                )

                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    logger.info(f"✅ Pollinations text OK ({model_id}): {len(content)} chars")
                    return content.strip()

                elif resp.status_code == 429:
                    wait = 15
                    logger.warning(f"Rate limit Pollinations ({model_id}), chờ {wait}s...")
                    time.sleep(wait)

                elif resp.status_code in [500, 502, 503]:
                    wait = 10
                    logger.warning(f"Server lỗi {resp.status_code} ({model_id}), chờ {wait}s...")
                    time.sleep(wait)

                elif resp.status_code == 402:
                    logger.error("❌ Hết Pollen! Nạp thêm tại enter.pollinations.ai")
                    raise RuntimeError("Insufficient Pollinations balance (402)")

                else:
                    logger.warning(f"HTTP {resp.status_code} từ Pollinations ({model_id}): {resp.text[:200]}")
                    time.sleep(5)

            except RuntimeError:
                raise
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout ({model_id}), lần {attempt+1}/{max_retries}")
                time.sleep(5)
            except Exception as e:
                last_error = e
                logger.warning(f"Lỗi ({model_id}), lần {attempt+1}: {e}")
                time.sleep(3)

        logger.info(f"Chuyển sang model tiếp theo...")

    raise RuntimeError(f"Pollinations text thất bại sau khi thử {len(models_to_try)} model. Lỗi: {last_error}")


def extract_json(text: str) -> dict:
    """
    Trích xuất JSON từ response text (xử lý markdown fences nếu có).
    """
    # Xóa markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'```$', '', text.strip()).strip()

    # Tìm JSON object trong text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group()

    return json.loads(text)
