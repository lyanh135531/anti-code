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
SHORTS_WORDS_MIN    = 65    # ~35s — đủ nội dung
SHORTS_WORDS_MAX    = 90    # ~50s — an toàn dưới 60s (Brian ≈ 110 WPM)


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
    curiosity_gap = topic_config.get("curiosity_gap", "What does this mean for me?")
    viral_pattern = topic_config.get("viral_pattern", "emotional_story")

    logger.info(f"Đang tạo script Shorts (Pollinations): {topic}")

    system = (
        "You are a YouTube Shorts scriptwriter and retention specialist for the channel 'Spiritus'. "
        "You create emotionally powerful, faith-inspiring short scripts about Jesus Christ. "
        "You always write in English and follow the exact format requested. "
        "Your scripts are designed to MAXIMIZE viewer retention — every second must earn the viewer's attention."
    )

    prompt = f"""Write a powerful, emotional 50-55 second YouTube Shorts script about Jesus Christ.

TOPIC: {topic}
OPENING HOOK: {hook}
BIBLE VERSE: {bible_ref}
VISUAL STYLE: {visual_theme}
KEYWORDS: {', '.join(keywords)}

CURIOUSITY GAP TO RESOLVE: {curiosity_gap}
VIRAL PATTERN: {viral_pattern}
→ The script MUST make the viewer think "{curiosity_gap}" after the hook.
→ The REVELATION segment MUST directly answer this question.
→ This is the #1 reason viewers will watch until the end.

═══════════════════════════════════════════════
RETENTION STRUCTURE — Follow this EXACT arc:
═══════════════════════════════════════════════

[HOOK — 0 to 3 seconds]
Purpose: STOP the scroll. Create curiosity or emotional shock.
The viewer should think "wait what?" and MUST keep watching.
Rule: Open with the hook line directly. NO warm-up. NO "today we talk about..."

[SETUP — 3 to 10 seconds]
Purpose: Create an information gap. Hint something surprising is coming.
Rule: 10-15 words MAX. Give just enough context to set up the revelation.

[RISING TENSION — 10 to 25 seconds]
Purpose: Build curiosity progressively. Each scene adds a new layer.
Rule: Each scene makes the viewer think "but what about...?" or "hmm interesting..."
Vary pacing: mix 3-word punchy lines with longer reflection lines.

[REVELATION/TWIST — 25 to 40 seconds]
Purpose: The "AHA!" moment. This is where retention peaks.
Rule: Deliver the surprising truth, the emotional punch, or hidden knowledge.
Make it COUNT — this is the reason viewers watch until the end.

[PAYOFF — 40 to 50 seconds]
Purpose: Emotional resolution. Connect back to the viewer's life.
Rule: Make them feel something deep. Connect the Bible truth to their daily struggle.

[CTA — Last 3-5 seconds]
Purpose: Drive engagement without being pushy.
Rule: 10 words max. "Follow for more" or "Share if this touched your heart."

═══════════════════════════════════════════════
STRICT RULES:
═══════════════════════════════════════════════

1. Write EXACTLY 9 scenes using format: [SCENE: description]
2. Total spoken words: 70-85 words (this is CRITICAL — must be under 58 seconds)
3. Each spoken line: 5-12 words. NO long sentences. Vary length for pacing.
4. Each [SCENE: ...] MUST describe a SPECIFIC Biblical/Christian visual in ANIME/PAINTING style.

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

5. Label each scene with its purpose: [SCENE-HOOK], [SCENE-SETUP], [SCENE-RISING], [SCENE-REVELATION], [SCENE-PAYOFF], [SCENE-CTA]
   (First scene = HOOK, second = SETUP, middle scenes = RISING/REVELATION, second-to-last = PAYOFF, last = CTA)
6. Tone: awe-inspiring, warm, faith-building

EXACT FORMAT (repeat 9 times):
[SCENE-XXX: specific Biblical/Christian visual prompt, include camera direction if helpful]
"Spoken line 5-12 words"
"Second line if needed"

Write the complete script now:"""

    raw_script = chat_complete(prompt, system=system, temperature=0.85)

    # Validate scene count
    scene_count = len(re.findall(r'\[SCENE', raw_script))
    if scene_count < 5:
        raise ValueError(f"Too few scenes generated: {scene_count}/{SHORTS_SCENES_COUNT}")

    # Validate emotional arc labels exist
    required_labels = ['SCENE-HOOK', 'SCENE-SETUP']
    for label in required_labels:
        if label not in raw_script:
            logger.warning(f"Missing scene label: {label} — script may lack proper retention structure")

    # Build clean script for TTS
    clean_script = re.sub(r'\[SCENE[^\]]*:.*?\]', '', raw_script)
    clean_script = '\n'.join(
        line.strip().strip('"')
        for line in clean_script.splitlines()
        if line.strip() and line.strip() not in ('', '""')
    )

    word_count = len(clean_script.split())
    if word_count < 30:
        raise ValueError(f"Script too short: {word_count} words")

    # ── Validate per-line word count ──────────────────────────
    # Each spoken line should be 5-12 words for proper pacing
    spoken_lines = [l.strip().strip('"') for l in raw_script.splitlines() 
                    if l.strip() and not l.strip().startswith('[SCENE')]
    long_lines = [l for l in spoken_lines if len(l.split()) > 12]
    short_lines = [l for l in spoken_lines if len(l.split()) < 3]
    if long_lines:
        logger.warning(f"Found {len(long_lines)} lines > 12 words — pacing may be too slow: {long_lines[0][:60]}...")
    if short_lines:
        logger.info(f"Found {len(short_lines)} short lines (< 3 words) — good for punchy pacing")

    # ── Hard trim nếu AI vẫn gen quá dài ──────────────────────
    # Mục tiêu: tối đa SHORTS_WORDS_MAX từ → ~50s audio → an toàn dưới 60s
    HARD_WORD_LIMIT = SHORTS_WORDS_MAX + 5  # buffer 5 từ (tighter than before)
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
    """Tách [SCENE-XXX: ...] và text tương ứng."""
    scenes = []
    # Match both old format [SCENE: ...] and new format [SCENE-HOOK: ...], [SCENE-SETUP: ...], etc.
    pattern = r'\[SCENE[^\]]*:\s*(.*?)\](.*?)(?=\[SCENE|$)'
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
