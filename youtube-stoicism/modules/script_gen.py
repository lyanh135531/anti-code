"""
==========================================================
  MODULE: SCRIPT GENERATOR — SHORTS ONLY (Pollinations AI)
  Tạo script YouTube Shorts 45-55 giây về Stoicism.
  Mỗi script gồm ĐÚNG 9 cảnh [SCENE: ...] với ảnh Philosophical/Stoic.
  Dùng Pollinations AI thay thế Gemini — không bị 429!
==========================================================
"""

import logging
import re
from modules.pollinations_text import chat_complete

logger = logging.getLogger(__name__)

SHORTS_SCENES_COUNT = 9
SHORTS_WORDS_MIN    = 65    # ~35s — đủ nội dung
SHORTS_WORDS_MAX    = 90    # ~50s — an toàn dưới 60s (Brian ≈ 110 WPM)


def generate_shorts_script(topic_config: dict) -> dict:
    """
    Tạo script YouTube Shorts hoàn chỉnh về Stoicism.
    - Thời lượng: 45-55 giây
    - Số cảnh: đúng 9 [SCENE: ...] với ảnh Stoic/Philosophical
    """
    topic        = topic_config["topic"]
    hook         = topic_config.get("shorts_hook", topic)
    visual_theme = topic_config.get("visual_theme", "Ancient Greek marble statues, moody lighting")
    bible_ref    = topic_config.get("philosopher_quote", "Amor Fati - Marcus Aurelius")
    keywords     = topic_config.get("keywords", ["stoicism", "philosophy", "mindset"])

    logger.info(f"Đang tạo script Shorts (Pollinations): {topic}")

    system = (
        "You are a Philosophy YouTube Shorts scriptwriter for the channel 'Stoicism Mind'. "
        "You create thought-provoking, emotionally powerful short scripts about Stoic philosophy. "
        "You always write in English and follow the exact format requested."
    )

    prompt = f"""Write a powerful, thought-provoking 45-55 second YouTube Shorts script about Stoicism.

TOPIC: {topic}
OPENING HOOK: {hook}
PHILOSOPHER QUOTE: {bible_ref}
VISUAL STYLE: {visual_theme}
KEYWORDS: {', '.join(keywords)}

STRICT RULES:
1. Write EXACTLY {SHORTS_SCENES_COUNT} scenes using format: [SCENE: description]
2. Total spoken words: MAXIMUM {SHORTS_WORDS_MAX} words total (this is CRITICAL — the video must be under 58 seconds)
   - Each scene gets MAXIMUM 10 spoken words (1-2 short phrases only, NO long sentences)
   - Count carefully: {SHORTS_SCENES_COUNT} scenes × 10 words = 90 words max
3. Each [SCENE: ...] MUST describe a SPECIFIC Stoic/Philosophical visual in ANIME/PAINTING style.
   FACE RULES — VERY IMPORTANT:
   ❌ NEVER write "close-up face of Marcus Aurelius/person" — this causes AI face distortions
   ✅ INSTEAD use: wide shots, silhouettes, back views, hands only, symbolic objects, landscapes, marble statues
   
   GOOD examples:
   ✅ "Silhouette of a Greek philosopher standing on a mountain at sunrise, anime painting style"
   ✅ "Ancient Greek marble statue in the rain, cinematic dark mood, Studio Ghibli style"
   ✅ "A burning candle on an old wooden desk with ancient scrolls, dark academia style"
   ✅ "A lone warrior walking through a snowstorm, anime cinematic style, moody lighting"
   ✅ "Hourglass with sand falling slowly, dramatic lighting, cinematic painting"
   
   BAD examples:
   ❌ "Close-up of Marcus Aurelius face filled with wisdom"
   ❌ "Realistic portrait of a man looking at camera"
   ❌ "Photorealistic face of an ancient philosopher"

4. Spoken text per scene: MAXIMUM 10 words (1-2 short punchy lines — NOT full sentences)
5. Open with the hook line (under 10 words). Close with an ultra-short call-to-action or final thought.
6. Tone: thought-provoking, deep, motivational

EXACT FORMAT (repeat {SHORTS_SCENES_COUNT} times):
[SCENE: specific Stoic/Philosophical visual prompt]
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
    if word_count < 30:
        raise ValueError(f"Script too short: {word_count} words")

    # ── Hard trim nếu AI vẫn gen quá dài ─────────────────────────────────
    # Mục tiêu: tối đa SHORTS_WORDS_MAX từ → ~50s audio → an toàn dưới 60s
    HARD_WORD_LIMIT = SHORTS_WORDS_MAX + 10  # buffer 10 từ
    if word_count > HARD_WORD_LIMIT:
        logger.warning(
            f"Script quá dài ({word_count} từ > {HARD_WORD_LIMIT}). "
            f"Tự động cắt để đảm bảo dưới 60s..."
        )
        words = clean_script.split()
        trimmed = " ".join(words[:HARD_WORD_LIMIT])
        # Cắt tại câu hoàn chỉnh gần nhất
        for punct in ('.', '!', '?'):
            last_sent = trimmed.rfind(punct)
            if last_sent > len(trimmed) // 2:
                trimmed = trimmed[:last_sent + 1]
                break
        clean_script = trimmed
        word_count = len(clean_script.split())
        logger.info(f"Script sau khi cắt: {word_count} từ")
    # ─────────────────────────────────────────────────────────────────────

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
