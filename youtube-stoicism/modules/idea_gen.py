"""
==========================================================
  MODULE: IDEA GENERATOR — SHORTS CHỦ ĐỀ STOICISM
  Dùng Pollinations AI (không phải Gemini) — không bị 429!
==========================================================
"""

import logging
import os
from modules.pollinations_text import chat_complete, extract_json

logger = logging.getLogger(__name__)

HISTORY_FILE = ".topic_history.txt"


def _get_past_topics() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()][-50:]


def _save_topic_to_history(topic: str):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{topic}\n")


def generate_new_topic() -> dict:
    """
    Sáng tạo một chủ đề Shorts mới về Stoicism và Triết học.
    Chủ đề PHẢI cụ thể, sâu sắc và trực tiếp liên quan đến Stoic Mindset.
    """
    logger.info("Đang sáng tạo chủ đề Shorts về Stoicism (Pollinations)...")

    past_topics = _get_past_topics()
    history_str = "\n".join([f"- {t}" for t in past_topics]) if past_topics else "None yet."

    system = (
        "You are a YouTube Shorts content strategist and viral topic specialist for a philosophy and mindset channel called 'Stoicism Mind' "
        "dedicated EXCLUSIVELY to Stoicism, ancient wisdom, and modern mindset. "
        "Your job is to create powerful, thought-provoking short video topics about Stoic philosophy specifically. "
        "You understand viral content patterns and know how to create curiosity gaps that make people STOP scrolling."
    )

    prompt = f"""Generate ONE new YouTube Shorts topic about STOICISM for the Stoicism Mind channel.

RECENTLY COVERED TOPICS (DO NOT duplicate):
{history_str}

═══════════════════════════════════════════════
VIRAL TOPIC PATTERNS — Choose ONE for this video:
═══════════════════════════════════════════════

1. CONTRARIAN — "Most people believe X, but the truth is Y"
   → "Most people think Stoicism is about suppressing emotions. They're wrong."
   → "Marcus Aurelius did something that contradicts his own philosophy."

2. HIDDEN KNOWLEDGE — "There's a secret about X nobody talks about"
   → "The Stoic technique that ancient Romans used to stay calm."
   → "This hidden teaching from Epictetus changes everything."

3. EMOTIONAL STORY — "A person was going through X when Y happened"
   → "A soldier used this Stoic principle to survive captivity."
   → "He lost everything. Then he discovered Stoicism."

4. TRANSFORMATION — "I used to think X, then I discovered Y"
   → "I used to overthink everything. Then I found this Stoic practice."
   → "This one quote from Marcus Aurelius changed my entire life."

5. SHOCKING FACT — "X will blow your mind"
   → "The Stoic secret that modern psychology just discovered."
   → "What Seneca did with his money will shock you."

6. RELATABLE STRUGGLE — "If you're dealing with X, this is for you"
   → "If you can't stop overthinking, watch this."
   → "When life feels overwhelming, remember this Stoic truth."

═══════════════════════════════════════════════
STRICT REQUIREMENTS:
═══════════════════════════════════════════════

- The topic MUST specifically mention Stoic philosophers (Marcus Aurelius, Seneca, Epictetus, etc.) or core Stoic concepts (Amor Fati, Memento Mori, discipline, emotional control).
- Focus on: practical life advice, handling adversity, mastering emotions, focus, discipline, and ancient wisdom applied to modern life.
- The hook must create URGENCY and EMOTION — make viewers stop scrolling.
- The topic title MUST follow the chosen viral pattern structure.

Return ONLY a valid JSON object:
{{
  "topic": "A viral Shorts title about Stoicism (max 60 chars, MUST follow the chosen pattern)",
  "viral_pattern": "contrarian|hidden_knowledge|emotional_story|transformation|shocking_fact|relatable_struggle",
  "curiosity_gap": "The specific question the viewer will have after seeing the title/hook — what makes them NEED to watch until the end",
  "keywords": ["stoicism", "philosophy", "mindset", "discipline", "motivation"],
  "shorts_hook": "One explosive hook sentence to open the 50-second video (start with a profound quote or a psychological fact)",
  "visual_theme": "One sentence describing the overall visual style (e.g. 'Ancient Greek marble statues in rain, dark moody lighting')",
  "philosopher_quote": "One specific quote from a Stoic philosopher"
}}"""

    raw = chat_complete(prompt, system=system, temperature=0.9, json_mode=True)
    topic_config = extract_json(raw)

    required = ["topic", "keywords", "shorts_hook", "visual_theme", "philosopher_quote", "viral_pattern", "curiosity_gap"]
    for key in required:
        if key not in topic_config:
            raise ValueError(f"Missing key in topic response: '{key}'")

    # Validate viral_pattern value
    valid_patterns = ["contrarian", "hidden_knowledge", "emotional_story", "transformation", "shocking_fact", "relatable_struggle"]
    if topic_config["viral_pattern"] not in valid_patterns:
        logger.warning(f"Unknown viral_pattern: {topic_config['viral_pattern']} — defaulting to 'emotional_story'")
        topic_config["viral_pattern"] = "emotional_story"

    topic_config["religion"] = "Stoicism"
    _save_topic_to_history(topic_config["topic"])
    logger.info(f"✅ Topic về Stoicism: {topic_config['topic']}")
    return topic_config
