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
    return genai.GenerativeModel("gemini-2.5-flash")


def generate_video_script(topic_config: dict) -> dict:
    """
    Tạo nội dung script cho video dài (7-10 phút).
    
    Args:
        topic_config: Dict từ RELIGION_TOPICS trong config.py
        
    Returns:
        Dict chứa: script, title, description, tags, hook
    """
    topic   = topic_config["topic"]
    religion = topic_config["religion"]
    angle   = topic_config.get("script_angle", "")
    keywords = topic_config.get("keywords", [])

    logger.info(f"Đang tạo script cho topic: {topic}")

    model = _configure_gemini()

    prompt = f"""You are an expert YouTube content creator specializing in world religions and spirituality.

Create a complete, engaging YouTube video script on the following topic:

TOPIC: {topic}
RELIGION FOCUS: {religion}
ANGLE: {angle}
KEYWORDS TO NATURALLY INCLUDE: {', '.join(keywords)}

SCRIPT REQUIREMENTS:
- Total length: 900-1100 words (for a 7-9 minute video when read at normal pace)
- Language: Clear, engaging English for an international audience
- Tone: Respectful, educational, and inspiring — NOT preachy
- Structure:
  1. HOOK (30-40 words): Start with a powerful question or surprising fact that grabs attention instantly
  2. INTRO (60-80 words): Brief overview of what viewers will learn — include the phrase "Stay until the end because..."
  3. MAIN CONTENT (750-880 words): 4-5 sections with clear headings, each with stories/examples/facts
  4. OUTRO (80-100 words): Summarize key takeaways, ask viewers to comment their thoughts, remind them to Subscribe and Like

IMPORTANT RULES:
- Each section should feel like a natural conversation, not a textbook
- Include at least 2 specific historical facts or stories
- Include 1-2 surprising or lesser-known facts
- End sentences with natural spoken rhythm (short sentences are good)
- Do NOT use bullet points in the script — write in flowing paragraphs as if speaking
- Add [PAUSE] markers where the narrator should pause for effect
- Format each section with the heading in ALL CAPS like: [SECTION: Title Here]

Now write the complete script:"""

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.85,
                    max_output_tokens=2048,
                )
            )
            script_text = response.text
            logger.info(f"Script tạo thành công: {len(script_text.split())} từ")
            return {
                "topic":    topic,
                "religion": religion,
                "keywords": keywords,
                "script":   script_text,
                "word_count": len(script_text.split()),
            }
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/3 thất bại: {e}")
            if attempt < 2:
                time.sleep(5)

    raise RuntimeError("Không thể tạo script sau 3 lần thử")


def generate_shorts_script(topic_config: dict, full_script: str) -> str:
    """
    Tạo script ngắn 55-58 giây cho YouTube Shorts.
    
    Args:
        topic_config: Thông tin chủ đề
        full_script:  Script đầy đủ đã tạo trước đó
        
    Returns:
        Script ngắn dưới 150 từ
    """
    hook   = topic_config.get("shorts_hook", topic_config["topic"])
    topic  = topic_config["topic"]

    logger.info("Đang tạo script cho Shorts...")

    model = _configure_gemini()

    prompt = f"""Create an ultra-engaging YouTube Shorts script (55-58 seconds when read at normal pace = 120-140 words).

TOPIC: {topic}
HOOK IDEA: {hook}

CONTEXT FROM FULL VIDEO:
{full_script[:800]}

SHORTS SCRIPT REQUIREMENTS:
- Total: EXACTLY 120-140 words
- Start with the HOOK (5-7 words) — make it shocking/intriguing
- Then deliver 3 fast punchy facts or insights from the topic
- End with "Follow for more sacred wisdom!" or similar CTA
- Every sentence must be SHORT (max 12 words each)
- Read in a fast, energetic pace
- Add [PAUSE 0.5s] for dramatic effect

Write ONLY the script text, no instructions or meta-comments:"""

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,
                    max_output_tokens=400,
                )
            )
            shorts_script = response.text.strip()
            word_count = len(shorts_script.split())
            logger.info(f"Shorts script: {word_count} từ")
            return shorts_script
        except Exception as e:
            logger.warning(f"Shorts attempt {attempt+1}/3 thất bại: {e}")
            if attempt < 2:
                time.sleep(5)

    # Fallback: Dùng 140 từ đầu của full script
    words = full_script.split()[:140]
    return " ".join(words)


def save_script(script_text: str, filename: str, output_dir) -> str:
    """Lưu script ra file txt."""
    filepath = output_dir / f"{filename}.txt"
    filepath.write_text(script_text, encoding="utf-8")
    logger.info(f"Script đã lưu: {filepath}")
    return str(filepath)
