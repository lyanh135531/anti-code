"""
==========================================================
  MODULE: SCRIPT GENERATOR — SHORTS ONLY
  Tạo script YouTube Shorts 45-55 giây về Chúa Jesus.
  Mỗi script gồm ĐÚNG 9 cảnh [SCENE: ...] với ảnh Kinh Thánh.
  Dùng Gemini với Cloudflare Workers AI làm fallback.
==========================================================
"""

import logging
import re
from modules.ai_text import chat_complete

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
    visual_theme = topic_config.get(
        "visual_theme",
        "Masterpiece Renaissance oil painting with dramatic Caravaggio chiaroscuro lighting and Rembrandt golden highlights",
    )

    bible_ref    = topic_config.get("bible_reference", "John 3:16")
    keywords     = topic_config.get("keywords", ["jesus", "bible", "faith"])
    viewer_struggle = topic_config.get("viewer_struggle", "feeling unseen and alone")
    curiosity_gap = topic_config.get("curiosity_gap", "What does this mean for me?")
    revelation = topic_config.get("revelation", "Jesus meets people in their deepest need")
    emotional_payoff = topic_config.get(
        "emotional_payoff", "The viewer can take one faithful next step"
    )
    comment_question = topic_config.get(
        "comment_question", "What do you need to trust God with today?"
    )
    viral_pattern = topic_config.get("viral_pattern", "human_crisis")

    logger.info(f"Đang tạo script Shorts: {topic}")

    system = (
        "You are the lead writer and retention editor for Spiritus. You write accurate, "
        "reverent, contemplative Christian Shorts in natural spoken English, aligned with universal "
        "Biblical and Catholic-friendly spirituality. Every scene must advance one story: tension, "
        "discovery, scriptural revelation, and personal resolution. Use vivid concrete language, "
        "short rhythmic sentences, and second-person relevance. "
        "Never use Protestant altar-call tropes ('say this prayer to be saved'), hellfire scare tactics, "
        "anti-tradition polemics, or sensational clickbait. Follow the requested format exactly."
    )


    prompt = f"""Write a powerful, emotional 50-55 second YouTube Shorts script about Jesus Christ.

TOPIC: {topic}
OPENING HOOK: {hook}
BIBLE VERSE: {bible_ref}
VISUAL STYLE: {visual_theme}
KEYWORDS: {', '.join(keywords)}

VIEWER'S REAL STRUGGLE: {viewer_struggle}
OPEN QUESTION TO RESOLVE: {curiosity_gap}
SCRIPTURAL REVELATION: {revelation}
EMOTIONAL PAYOFF: {emotional_payoff}
FINAL COMMENT QUESTION: {comment_question}
VIRAL PATTERN: {viral_pattern}

The hook must make the viewer silently ask: "{curiosity_gap}"
Scenes 2-6 must delay—but continually earn—the answer with new information.
Scenes 7-8 must answer it clearly through {bible_ref} and connect it to the viewer's struggle.

═══════════════════════════════════════════════
RETENTION STRUCTURE — Follow this EXACT arc:
═══════════════════════════════════════════════

[HOOK — 0 to 3 seconds]
Use the supplied hook or improve it. Deliver 4-8 sharp words before any context.
Create tension without exaggeration. No greetings, setup, quotation label, or warm-up.

[SETUP — 3 to 10 seconds]
Place the viewer inside one concrete emotional moment. Withhold the answer.

[RISING TENSION — 10 to 25 seconds]
Add one new fact, contrast, or consequence per scene. Never paraphrase the previous line.
End at least two lines with an unresolved implication that naturally pulls forward.

[REVELATION/TWIST — 25 to 40 seconds]
Answer the exact open question with the passage's real meaning.
If quoting Scripture, use only a short accurate excerpt; otherwise paraphrase faithfully.

[PAYOFF — 40 to 50 seconds]
Echo an image or phrase from the hook. Give one specific reframe or next action.

[CTA — Last 3-5 seconds]
Ask the supplied reflection question in 10 words or fewer. It should invite an honest comment,
not a forced declaration. A subtle follow prompt is optional.

═══════════════════════════════════════════════
STRICT RULES:
═══════════════════════════════════════════════

1. Write EXACTLY 9 scenes in this order:
   HOOK, SETUP, RISING, RISING, RISING, REVELATION, REVELATION, PAYOFF, CTA.
2. Total spoken words: 70-85. Count only spoken lines.
3. Use one spoken line per scene, normally 5-11 words. Mix short punches with flowing lines.
4. Use simple conversational English. Prefer concrete nouns and active verbs.
5. Do not repeat the hook, verse, lesson, or emotional claim in different words.
6. Do not use clichés such as "everything happens for a reason", "you needed to hear this",
   "God is saying", "this changes everything", or "let that sink in".
7. The message must be theologically responsible and supported by {bible_ref}.
8. Write in a reverent, contemplative Biblical tone. Do not use Protestant altar calls ('say this prayer to be saved'), hellfire scare tactics ('turn to Jesus or go to hell'), or attacks on church tradition/pastors.
9. PURE SPOKEN NARRATIVE ONLY: Spoken lines must contain ONLY pure, natural spoken narrative message intended for the listener. NEVER include technical terms, stage directions, scene labels ('Scene 1', 'VO:', 'Narrator:'), Bible citation brackets like '(John 3:16)', or meta instructions.



VISUAL RULES FOR EVERY [SCENE-...: description]:
- Describe one distinct fine-art composition inspired by Renaissance and Baroque masters.
- Style: Masterpiece oil painting in the style of Caravaggio and Rembrandt, 17th century baroque fine art, dramatic chiaroscuro contrast, deep rich shadows, luminous divine rays, classical oil on canvas.
- Palette: Rich deep umber, ochre, warm gold, crimson, and deep dark background shadows pierced by intense divine beam of light.
- COMPOSITION & FIGURES: Show dramatic scenes with strong depth. Avoid using explicit names like 'Jesus' or 'God' inside [SCENE: ...] visual descriptions to prevent safety filter false-positives. Instead, use terms like 'a noble figure in traditional robes', 'a cloaked traveler', 'a divine presence of light', or 'a reverent teacher'. Show people in shadow, silhouette, side view, or obscured by robes and light.

- Use one strong symbol per frame: doorway, dusty path, oil lamp, cross, fishing boat, bread, empty tomb, storm waves, olive tree, or a figure beneath dramatic skies.
- Maintain a cohesive Renaissance art aesthetic across all nine scenes.
- Never request anime, photorealism 3D render, glossy graphics, neon colors, readable text, or watermarks.

GOOD VISUAL EXAMPLES:
- "A dramatic chiaroscuro oil painting of a solitary traveler on a dusty Judean path, bathed in a single beam of divine golden light, deep Rembrandt shadows, fine art canvas"
- "A masterwork Baroque oil painting of a storm at sea, dramatic contrast between dark swirling waves and radiant divine light piercing through storm clouds, Caravaggio lighting"
- "A serene Renaissance composition of an empty stone tomb at dawn, a beam of warm heavenly light illuminating folded linen on stone, deep chiaroscuro contrast"

EXACT FORMAT (repeat 9 times):
[SCENE-XXX: one fine-art Renaissance composition following all visual rules]
"One spoken line"


Write the complete script now:"""

    raw_script = chat_complete(prompt, system=system, temperature=0.85)

    # Validate scene count
    scene_count = len(re.findall(r'\[SCENE', raw_script))
    if scene_count != SHORTS_SCENES_COUNT:
        raise ValueError(
            f"Expected exactly {SHORTS_SCENES_COUNT} scenes, received {scene_count}"
        )

    # Validate emotional arc labels exist
    required_labels = ['SCENE-HOOK', 'SCENE-SETUP']
    for label in required_labels:
        if label not in raw_script:
            logger.warning(f"Missing scene label: {label} — script may lack proper retention structure")

    # Build clean script for TTS (pure spoken narrative only, no technical/meta labels)
    clean_script = re.sub(r'\[SCENE[^\]]*:.*?\]', '', raw_script)
    clean_script = re.sub(r'\[[^\]]*\]', '', clean_script)
    clean_script = re.sub(r'\([^)]*\)', '', clean_script)
    
    clean_lines = []
    for line in clean_script.splitlines():
        l = line.strip().strip('"\'')
        l = re.sub(r'^(VO|Voiceover|Narrator|Hook|Setup|Rising|Revelation|Payoff|CTA|Scene\s*\d+)\s*:\s*', '', l, flags=re.IGNORECASE)
        l = l.strip().strip('"\'')
        if l:
            clean_lines.append(l)

    clean_script = '\n'.join(clean_lines)


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
