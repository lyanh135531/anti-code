"""
==========================================================
  MODULE: IDEA GENERATOR — SHORTS CHỦ ĐỀ CHÚA JESUS
  Dùng Gemini với Cloudflare Workers AI làm fallback.
==========================================================
"""

import logging
import os
from modules.ai_text import chat_complete, extract_json

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
    Sáng tạo một chủ đề Shorts mới về Chúa Jesus và Kinh Thánh.
    Chủ đề PHẢI cụ thể, xúc động và trực tiếp liên quan đến Jesus Christ.
    """
    logger.info("Đang sáng tạo chủ đề Shorts về Chúa Jesus...")

    past_topics = _get_past_topics()
    history_str = "\n".join([f"- {t}" for t in past_topics]) if past_topics else "None yet."

    system = (
        "You are the senior YouTube Shorts strategist for Spiritus, a Christian channel "
        "about Jesus Christ and the Bible. You design truthful, emotionally resonant ideas "
        "that earn attention through a precise human struggle, a credible open loop, and a "
        "specific scriptural payoff. You never invent testimony, distort Scripture, use fearbait, "
        "or promise a revelation the video cannot deliver. Write concise natural English for a "
        "broad mobile audience."
    )

    prompt = f"""Create ONE high-retention YouTube Shorts concept about JESUS CHRIST for Spiritus.

RECENTLY COVERED TOPICS (DO NOT duplicate):
{history_str}

═══════════════════════════════════════════════
CHOOSE ONE RETENTION ANGLE:
═══════════════════════════════════════════════

1. PARADOX — A teaching of Jesus sounds impossible until its meaning becomes clear.
2. OVERLOOKED DETAIL — One small, verifiable detail in a Gospel scene changes its meaning.
3. HUMAN CRISIS — Fear, grief, shame, loneliness, doubt, or waiting meets a specific teaching.
4. QUESTION — Ask one emotionally urgent question that Scripture answers near the end.
5. REFRAME — Replace a common but shallow interpretation with the passage's actual message.
6. DIRECT ADDRESS — Speak to one viewer in one recognizable moment of struggle.

═══════════════════════════════════════════════
RETENTION REQUIREMENTS:
═══════════════════════════════════════════════

- Anchor the concept in ONE specific verse or Gospel event and preserve its real context.
- Target ONE concrete viewer struggle; never use generic "life is hard" language.
- Create ONE open question in the hook and give its complete answer in the payoff.
- The hook must be 6-11 spoken words, immediately understandable, and address the viewer.
- Start with tension, a paradox, or an unexpected image. Do not start with "Did you know", "Imagine", "Today", or "The Bible says".
- The payoff must offer a useful spiritual reframe, not merely repeat the verse.
- Avoid fabricated stories, vague miracles, prophecy claims, attacks on churches, and manipulative phrases such as "this will shock you" or "watch until the end".
- Make the concept materially different from every recent topic above.
- Plan a final, specific reflection question that viewers can answer in comments.

VISUAL DIRECTION:
- Every image will be a symbolic, semi-abstract oil painting.
- Use indistinct human silhouettes, simplified forms, soft edges, visible impasto brushwork, atmospheric haze, and allegorical objects.
- Every human figure must be faceless: show only distant back views, tiny silhouettes, cropped
  bodies, or heads fully hidden by shadow, haze, cloth, or light. Never show identifiable eyes,
  noses, mouths, facial contours, front-facing people, portraits, or close-ups.
- Avoid photorealism, anime, crisp digital art, readable text, and literal close-ups.
- Use a cohesive sunset palette: antique gold, amber, burnt orange, ochre, umber, and deep brown shadows.

Return ONLY a valid JSON object:
{{
  "topic": "Specific compelling title, 38-58 characters",
  "viral_pattern": "paradox|overlooked_detail|human_crisis|question|reframe|direct_address",
  "viewer_struggle": "One concrete emotional situation the viewer recognizes",
  "curiosity_gap": "The single unanswered question created by the hook",
  "revelation": "The accurate scriptural truth that answers the question",
  "emotional_payoff": "How that truth changes the viewer's next thought or action",
  "comment_question": "A short, specific reflection question tied to the message",
  "keywords": ["five focused lowercase search terms"],
  "shorts_hook": "A 6-11 word spoken hook with tension and an open loop",
  "visual_theme": "Faceless distant silhouettes in symbolic semi-abstract oil paintings, thick brushwork, golden-orange sunset haze",
  "bible_reference": "One specific and contextually accurate Bible reference"
}}"""

    raw = chat_complete(prompt, system=system, temperature=0.9, json_mode=True)
    topic_config = extract_json(raw)

    required = [
        "topic",
        "keywords",
        "shorts_hook",
        "visual_theme",
        "bible_reference",
        "viral_pattern",
        "viewer_struggle",
        "curiosity_gap",
        "revelation",
        "emotional_payoff",
        "comment_question",
    ]
    for key in required:
        if key not in topic_config:
            raise ValueError(f"Missing key in topic response: '{key}'")

    # Validate viral_pattern value
    valid_patterns = [
        "paradox",
        "overlooked_detail",
        "human_crisis",
        "question",
        "reframe",
        "direct_address",
    ]
    if topic_config["viral_pattern"] not in valid_patterns:
        logger.warning(
            f"Unknown viral_pattern: {topic_config['viral_pattern']} — defaulting to 'human_crisis'"
        )
        topic_config["viral_pattern"] = "human_crisis"

    topic_config["religion"] = "Christianity"
    _save_topic_to_history(topic_config["topic"])
    logger.info(f"✅ Topic về Chúa Jesus: {topic_config['topic']}")
    return topic_config
