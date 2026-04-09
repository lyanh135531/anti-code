"""
==========================================================
  MODULE: SCRIPT GENERATOR (NEW SDK)
  Dùng Google Gemini API (google-genai) để tạo nội dung video
==========================================================
"""

import logging
import time
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MAIN_MODEL, GEMINI_FALLBACK_MODELS

logger = logging.getLogger(__name__)


def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_video_script(topic_config: dict) -> dict:
    """
    Tạo nội dung script cho video dài (7-10 phút) sử dụng SDK mới.
    """
    topic   = topic_config["topic"]
    religion = topic_config["religion"]
    angle   = topic_config.get("script_angle", "")
    keywords = topic_config.get("keywords", [])

    logger.info(f"Đang tạo script cho topic: {topic}")

    client = _get_client()
    
    # Danh sách các model để thử (Primary + Fallbacks)
    model_list = [GEMINI_MAIN_MODEL] + GEMINI_FALLBACK_MODELS
    
    prompt = f"""You are an expert YouTube content creator specializing in world religions and spirituality.
Target Audience: Global (International). Language: English.

Create a complete, engaging YouTube video script on the following topic:

TOPIC: {topic}
RELIGION FOCUS: {religion}
ANGLE: {angle}
KEYWORDS TO NATURALLY INCLUDE: {', '.join(keywords)}

SCRIPT REQUIREMENTS:
- Total length: 900-1100 words (for a 7-9 minute video)
- Tone: Respectful, educational, and inspiring.
- Visuals: For EVERY major paragraph, include a [SCENE: ...] tag describing a high-quality, cinematic visual prompt for an AI image generator (Imagen).

Structure:
  1. HOOK (30-40 words): Start with a powerful question or surprising fact.
  2. INTRO (60-80 words): Brief overview.
  3. MAIN CONTENT: 4-5 sections with clear headings [SECTION: Title].
  4. OUTRO: Summary and CTA (Subscribe/Like).

Format:
[SCENE: Detailed cinematic prompt for AI image generator]
"Spoken script text here..."

Now write the complete script in English:"""

    last_error = None
    for model_id in model_list:
        logger.info(f"Sử dụng model: {model_id}")
        
        for attempt in range(2): # 2 attempts per model
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.8,
                        max_output_tokens=4000,
                    )
                )
                
                script_text = response.text
                if not script_text:
                    raise ValueError("Nhận được phản hồi rỗng từ AI.")
                    
                word_count = len(script_text.split())
                if word_count < 100:
                    raise ValueError(f"Script tạo ra quá ngắn ({word_count} từ).")
                    
                logger.info(f"Script tạo thành công: {word_count} từ")
                return {
                    "topic":    topic,
                    "religion": religion,
                    "keywords": keywords,
                    "script":   script_text,
                    "word_count": word_count,
                }
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                logger.warning(f"Lỗi với model {model_id} (lần {attempt+1}): {err_str}")
                
                if "429" in err_str or "quota" in err_str:
                    wait_time = 30
                    logger.info(f"Hết quota, chờ {wait_time}s...")
                    time.sleep(wait_time)
                elif "503" in err_str or "unavailable" in err_str:
                    wait_time = 10
                    logger.info(f"Dịch vụ quá tải, chờ {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    time.sleep(5)
        
        logger.info(f"Thử model tiếp theo...")

    raise RuntimeError(f"Không thể tạo script sau khi thử tất cả các model. Lỗi cuối: {last_error}")


def generate_shorts_script(topic_config: dict, full_script: str) -> str:
    """
    Tạo script ngắn 55-58 giây cho YouTube Shorts.
    """
    hook   = topic_config.get("shorts_hook", topic_config["topic"])
    topic  = topic_config["topic"]

    logger.info("Đang tạo script cho Shorts...")

    client = _get_client()
    model_list = [GEMINI_MAIN_MODEL] + GEMINI_FALLBACK_MODELS

    prompt = f"""Create an ultra-engaging YouTube Shorts script in English (55-58 seconds).
TOPIC: {topic}
HOOK IDEA: {hook}

CONTEXT FROM FULL VIDEO:
{full_script[:1500]}

SHORTS SCRIPT REQUIREMENTS:
- Total spoken words: 120-140 words.
- Visual Scenes: You MUST include EXACTLY 8 visual scene prompts using the format [SCENE: Description].
- Prompts should be cinematic, 8k, photorealistic, and match the spoken text.
- Captions style: The spoken text should be divided into short, punchy phrases.

Format:
[SCENE: Visual prompt for Imagen]
"Spoken phrase 1..."
"Spoken phrase 2..."

[SCENE: Visual prompt 2]
"Spoken phrase 3..."

... continue until you have 8 scenes.

Write ONLY the script in English:"""

    last_error = None
    for model_id in model_list:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.9,
                    max_output_tokens=1500,
                )
            )
            
            shorts_script = response.text.strip()
            # Kiểm tra sơ bộ định dạng
            scene_count = len(re.findall(r'\[SCENE:', shorts_script))
            if scene_count < 3:
                raise ValueError(f"Định dạng Shorts script không chuẩn (chỉ có {scene_count} cảnh).")
                
            logger.info(f"Shorts script created with {scene_count} scenes.")
            return shorts_script
        except Exception as e:
            last_error = e
            logger.warning(f"Lỗi tạo Shorts với {model_id}: {e}")
            continue

    # Fallback basic format if AI fails completely
    return f"[SCENE: Cinematic portrait of {topic}]\n{full_script[:140]}"


def save_script(script_text: str, filename: str, output_dir) -> str:
    """Lưu script ra file txt."""
    filepath = output_dir / f"{filename}.txt"
    filepath.write_text(script_text, encoding="utf-8")
    logger.info(f"Script đã lưu: {filepath}")
    return str(filepath)
