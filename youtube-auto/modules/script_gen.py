"""
==========================================================
  MODULE: SCRIPT GENERATOR — SHORTS ONLY (Pollinations AI)
  Tạo script YouTube Shorts 45-55 giây về Chúa Jesus.
  Mỗi script gồm ĐÚNG 9 cảnh [SCENE: ...] với ảnh Kinh Thánh.
  Dùng Pollinations AI thay thế Gemini — không bị 429!
==========================================================
"""

import logging
import re
from modules.pollinations_text import chat_complete

logger = logging.getLogger(__name__)

SHORTS_SCENES_COUNT = 9
SHORTS_WORDS_MIN    = 100   # ~45s
SHORTS_WORDS_MAX    = 130   # ~58s


def generate_shorts_script(topic_config: dict) -> dict:
    """
    Tạo script YouTube Shorts hoàn chỉnh về Chúa Jesus.
    - Thời lượng: 45-55 giây
    - Số cảnh: đúng 9 [SCENE: ...] với ảnh Biblical/Christian
    """
    topic        = topic_config["topic"]
    hook         = topic_config.get("shorts_hook", topic)
    visual_theme = topic_config.get("visual_theme", "Ancient Jerusalem with divine golden light")
    bible_ref    = topic_config.get("bible_reference", "John 3:16")
    keywords     = topic_config.get("keywords", ["jesus", "bible", "faith"])

    logger.info(f"Đang tạo script Shorts (Pollinations): {topic}")

    system = (
        "You are a Christian YouTube Shorts scriptwriter for the channel 'Spiritus'. "
        "You create emotionally powerful, faith-inspiring short scripts about Jesus Christ. "
        "You always write in English and follow the exact format requested."
    )

    prompt = f"""Write a powerful, emotional 45-55 second YouTube Shorts script about Jesus Christ.

TOPIC: {topic}
OPENING HOOK: {hook}
BIBLE VERSE: {bible_ref}
VISUAL STYLE: {visual_theme}
KEYWORDS: {', '.join(keywords)}

STRICT RULES:
1. Write EXACTLY {SHORTS_SCENES_COUNT} scenes using format: [SCENE: description]
2. Total spoken words: {SHORTS_WORDS_MIN}–{SHORTS_WORDS_MAX} words
3. Each [SCENE: ...] MUST describe a SPECIFIC Biblical/Christian visual in ANIME/PAINTING style.
   FACE RULES — VERY IMPORTANT:
   ❌ NEVER write "close-up face of Jesus/person" — this causes AI face distortions
   ✅ INSTEAD use: wide shots, silhouettes, back views, hands only, symbolic objects, landscapes
   
   GOOD examples:
   ✅ "Silhouette of Jesus with arms open on a hilltop at sunset, anime painting style, golden sky"
   ✅ "Hands of Jesus gently touching an open Bible, warm candlelight, Studio Ghibli style"
   ✅ "Ancient Jerusalem skyline at dusk, anime art style, warm amber tones, cross on a hill"
   ✅ "A glowing dove descending from heaven through golden clouds, anime painting"
   ✅ "Open Bible with John 3:16 glowing softly, ethereal light, cinematic painting"
   ✅ "A wooden cross on a hilltop, dramatic sunset, anime cinematic style"
   ✅ "Person kneeling in prayer in silhouette inside a cathedral, golden light rays"
   
   BAD examples:
   ❌ "Close-up of Jesus's face filled with compassion"
   ❌ "Realistic portrait of a man looking at camera"
   ❌ "Photorealistic face of a grieving woman"

4. Spoken text per scene: 2–3 short punchy lines
5. Open with the hook line. Close with call-to-faith: "Follow for daily Scripture" or similar.
6. Tone: awe-inspiring, warm, faith-building

EXACT FORMAT (repeat {SHORTS_SCENES_COUNT} times):
[SCENE: specific Biblical/Christian visual prompt]
"Spoken line 1"
"Spoken line 2"

Write the complete script now:"""

    raw_script = chat_complete(prompt, system=system, temperature=0.85)

    # Validate scene count
    scene_count = len(re.findall(r'\[SCENE:', raw_script))
    if scene_count < 5:
        raise ValueError(f"Too few scenes generated: {scene_count}/{SHORTS_SCENES_COUNT}")

    # Build clean script for TTS
    clean_script = re.sub(r'\[SCENE:.*?\]', '', raw_script)
    clean_script = '\n'.join(
        line.strip().strip('"')
        for line in clean_script.splitlines()
        if line.strip() and line.strip() not in ('', '""')
    )

    word_count = len(clean_script.split())
    if word_count < 60:
        raise ValueError(f"Script too short: {word_count} words")

    scenes = _parse_scenes(raw_script)
    logger.info(f"✅ Script OK: {scene_count} cảnh, {word_count} từ")

    return {
        "topic":          topic,
        "script":         raw_script,
        "clean_script":   clean_script,
        "scenes":         scenes,
        "word_count":     word_count,
        "bible_reference": bible_ref,
    }


def _parse_scenes(script_text: str) -> list[dict]:
    """Tách [SCENE: ...] và text tương ứng."""
    scenes = []
    pattern = r'\[SCENE:\s*(.*?)\](.*?)(?=\[SCENE:|$)'
    matches = re.findall(pattern, script_text, re.DOTALL)

    for prompt, text in matches:
        clean_text = '\n'.join(
            line.strip().strip('"')
            for line in text.splitlines()
            if line.strip()
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
