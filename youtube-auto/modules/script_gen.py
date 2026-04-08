"""
==========================================================
  MODULE: SCRIPT GENERATOR
  Dùng Google Gemini API (miễn phí) để tạo nội dung video
==========================================================
"""

import logging
import time
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


def _configure_gemini():
    """Cấu hình Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-3-flash-preview")


def generate_video_script(topic_config: dict) -> dict:
    """
    Tạo nội dung script cho video dài (7-10 phút).
    Bao gồm các gợi ý cảnh quay [SCENE: ...] cho AI tạo ảnh.
    """
    topic   = topic_config["topic"]
    religion = topic_config["religion"]
    angle   = topic_config.get("script_angle", "")
    keywords = topic_config.get("keywords", [])

    logger.info(f"Đang tạo script cho topic: {topic}")

    model = _configure_gemini()

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

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.85,
                    max_output_tokens=3000,
                )
            )
            script_text = response.text
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
            err_str = str(e)
            logger.warning(f"Attempt {attempt+1}/3 thất bại: {err_str}")
            if attempt < 2:
                time.sleep(5)

    raise RuntimeError("Không thể tạo script sau 3 lần thử")


def generate_shorts_script(topic_config: dict, full_script: str) -> str:
    """
    Tạo script ngắn 55-58 giây cho YouTube Shorts.
    Yêu cầu chính xác 6-10 visual prompts [SCENE: ...].
    """
    hook   = topic_config.get("shorts_hook", topic_config["topic"])
    topic  = topic_config["topic"]

    logger.info("Đang tạo script cho Shorts...")

    model = _configure_gemini()

    prompt = f"""Create an ultra-engaging YouTube Shorts script in English (55-58 seconds).
TOPIC: {topic}
HOOK IDEA: {hook}

CONTEXT FROM FULL VIDEO:
{full_script[:1000]}

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

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,
                    max_output_tokens=1000,
                )
            )
            shorts_script = response.text.strip()
            # Kiểm tra số lượng [SCENE:]
            scene_count = len(re.findall(r'\[SCENE:', shorts_script))
            if scene_count < 4:
                raise ValueError(f"Số lượng cảnh quá ít ({scene_count}).")
            
            logger.info(f"Shorts script created with {scene_count} scenes.")
            return shorts_script
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Shorts attempt {attempt+1}/3 thất bại: {err_str}")
            if attempt < 2:
                time.sleep(5)

    # Fallback basic format if AI fails to format correctly
    return f"[SCENE: Cinematic portrait of {topic}]\n{full_script[:140]}"



def save_script(script_text: str, filename: str, output_dir) -> str:
    """Lưu script ra file txt."""
    filepath = output_dir / f"{filename}.txt"
    filepath.write_text(script_text, encoding="utf-8")
    logger.info(f"Script đã lưu: {filepath}")
    return str(filepath)
