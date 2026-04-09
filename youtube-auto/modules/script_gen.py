"""
==========================================================
  MODULE: SCRIPT GENERATOR — SHORTS ONLY
  Tạo script YouTube Shorts 45-55 giây về Chúa Jesus.
  Mỗi script gồm ĐÚNG 9 cảnh [SCENE: ...] với ảnh Kinh Thánh.
==========================================================
"""

import logging
import time
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MAIN_MODEL, GEMINI_FALLBACK_MODELS

logger = logging.getLogger(__name__)

SHORTS_SCENES_COUNT = 9   # 9 ảnh = 9 cảnh
SHORTS_WORDS_MIN    = 100  # ~45s at ~130 WPM
SHORTS_WORDS_MAX    = 130  # ~58s


def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_shorts_script(topic_config: dict) -> dict:
    """
    Tạo script YouTube Shorts hoàn chỉnh về Chúa Jesus.
    - Thời lượng: 45-55 giây
    - Số cảnh: đúng 9 [SCENE: ...] với ảnh Biblical/Christian
    - Không phụ thuộc vào long-form script nào.

    Returns:
        {
            "topic": str,
            "script": str,        # Full script with [SCENE: ...] markers
            "clean_script": str,  # Script without markers (for TTS)
            "scenes": list[dict], # List of {visual_prompt, text}
            "word_count": int,
            "bible_reference": str,
        }
    """
    topic           = topic_config["topic"]
    hook            = topic_config.get("shorts_hook", topic)
    visual_theme    = topic_config.get("visual_theme", "Ancient Jerusalem with divine golden light")
    bible_ref       = topic_config.get("bible_reference", "John 3:16")
    keywords        = topic_config.get("keywords", ["jesus", "bible", "faith"])

    logger.info(f"Đang tạo script Shorts: {topic}")

    client = _get_client()
    model_list = [GEMINI_MAIN_MODEL] + GEMINI_FALLBACK_MODELS

    prompt = f"""You are a Christian YouTube Shorts scriptwriter. Write a powerful, emotional 45-55 second script about Jesus Christ for the channel "Spiritus".

TOPIC: {topic}
OPENING HOOK: {hook}
BIBLE VERSE TO FEATURE: {bible_ref}
VISUAL STYLE: {visual_theme}
KEYWORDS: {', '.join(keywords)}

STRICT RULES:
1. Write EXACTLY {SHORTS_SCENES_COUNT} scenes using this format: [SCENE: description]
2. Total spoken words: {SHORTS_WORDS_MIN}–{SHORTS_WORDS_MAX} words (this gives 45–55 seconds at normal pace)
3. Each [SCENE: ...] must describe a SPECIFIC Biblical or Christian visual:
   - Examples: "Jesus healing a blind man in ancient Jerusalem, golden sunlight", "Open Bible with John 3:16 glowing, ethereal light", "The cross on a hill at sunset, dramatic clouds"
   - NEVER generic: "a person meditating", "nature landscape", "peaceful scenery"
4. The spoken text under each scene must be short punchy phrases (2–3 lines max per scene)
5. Open with the hook. Close with a call-to-faith (e.g. "Subscribe for daily Scripture")
6. Emotional tone: awe-inspiring, warm, faith-building — never preachy or boring

FORMAT (repeat exactly {SHORTS_SCENES_COUNT} times):
[SCENE: specific Biblical/Christian visual prompt]
"Spoken line 1"
"Spoken line 2"

Write the complete script now:"""

    last_error = None
    for model_id in model_list:
        logger.info(f"Sử dụng model: {model_id}")
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.85,
                        max_output_tokens=2000,
                    )
                )

                script_text = response.text
                if not script_text:
                    raise ValueError("Phản hồi rỗng từ API.")

                # Validate scene count
                scene_count = len(re.findall(r'\[SCENE:', script_text))
                if scene_count < 6:
                    raise ValueError(f"Quá ít cảnh: {scene_count}/{SHORTS_SCENES_COUNT}")
                if scene_count > 12:
                    raise ValueError(f"Quá nhiều cảnh: {scene_count}")

                # Build clean script (TTS)
                clean_script = re.sub(r'\[SCENE:.*?\]', '', script_text)
                clean_script = re.sub(r'^\s*"(.*)"\s*$', r'\1', clean_script, flags=re.MULTILINE)
                clean_script = re.sub(r'\[SECTION:.*?\]', '', clean_script)
                clean_script = '\n'.join(
                    line.strip().strip('"') for line in clean_script.splitlines() if line.strip()
                )

                word_count = len(clean_script.split())
                if word_count < 60:
                    raise ValueError(f"Script quá ngắn: {word_count} từ")

                # Parse scenes
                scenes = _parse_scenes(script_text)

                logger.info(f"✅ Script OK ({model_id}): {scene_count} cảnh, {word_count} từ")
                return {
                    "topic":          topic,
                    "script":         script_text,
                    "clean_script":   clean_script,
                    "scenes":         scenes,
                    "word_count":     word_count,
                    "bible_reference": bible_ref,
                }

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Lỗi {model_id} (lần {attempt+1}): {err_str[:200]}")

                if "429" in err_str or "quota" in err_str:
                    logger.info(f"Hết quota {model_id} → chuyển model...")
                    break
                elif "503" in err_str or "unavailable" in err_str:
                    time.sleep(10)
                else:
                    time.sleep(5)

        logger.info("Thử model tiếp theo...")

    raise RuntimeError(f"Không thể tạo script sau khi thử tất cả model. Lỗi: {last_error}")


def _parse_scenes(script_text: str) -> list[dict]:
    """
    Tách [SCENE: ...] và phần text nói tương ứng.
    Trả về list [{'visual_prompt': '...', 'text': '...'}]
    """
    scenes = []
    pattern = r'\[SCENE:\s*(.*?)\](.*?)(?=\[SCENE:|$)'
    matches = re.findall(pattern, script_text, re.DOTALL)

    for prompt, text in matches:
        clean_text = re.sub(r'\[SECTION:.*?\]', '', text)
        clean_text = '\n'.join(
            line.strip().strip('"') for line in clean_text.splitlines() if line.strip()
        )
        if prompt.strip():
            scenes.append({
                "visual_prompt": prompt.strip(),
                "text": clean_text.strip(),
            })

    return scenes


def save_script(script_text: str, filename: str, output_dir) -> str:
    """Lưu script ra file txt."""
    filepath = output_dir / f"{filename}.txt"
    filepath.write_text(script_text, encoding="utf-8")
    logger.info(f"Script đã lưu: {filepath}")
    return str(filepath)
