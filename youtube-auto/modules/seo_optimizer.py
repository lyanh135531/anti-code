"""
==========================================================
  MODULE: SEO OPTIMIZER
  Tạo title, description, tags tối ưu SEO cho YouTube Shorts.
  Dùng Gemini với Cloudflare Workers AI làm fallback.
==========================================================
"""

import logging
from modules.ai_text import chat_complete, extract_json
from config import BASE_TAGS, CHANNEL_NAME

logger = logging.getLogger(__name__)


def generate_seo_metadata(topic_config: dict, script: str) -> dict:
    """
    Tạo SEO metadata cho YouTube Shorts bằng AI.
    """
    topic    = topic_config["topic"]
    keywords = topic_config.get("keywords", [])
    bible    = topic_config.get("bible_reference", "")
    viewer_struggle = topic_config.get("viewer_struggle", "")
    revelation = topic_config.get("revelation", "")
    emotional_payoff = topic_config.get("emotional_payoff", "")
    comment_question = topic_config.get("comment_question", "")

    logger.info("Đang tạo SEO metadata...")

    system = (
        "You are the packaging editor for Spiritus, a Christian YouTube Shorts channel. "
        "Create truthful, specific metadata that earns the click by naming a real emotional "
        "tension and promising the exact scriptural insight delivered in the video. Write in "
        "natural English for people, not search engines. Never fabricate testimony, attack "
        "churches, exploit fear, or make a promise the script cannot fulfill."
    )

    prompt = f"""Generate SEO metadata for a YouTube Shorts video about Jesus Christ.

VIDEO TOPIC: {topic}
BIBLE REFERENCE: {bible}
PRIMARY KEYWORDS: {', '.join(keywords)}
CHANNEL: {CHANNEL_NAME}
VIRAL PATTERN: {topic_config.get('viral_pattern', 'human_crisis')}
CURIOSITY GAP: {topic_config.get('curiosity_gap', '')}
VIEWER'S STRUGGLE: {viewer_struggle}
SCRIPTURAL REVELATION: {revelation}
EMOTIONAL PAYOFF: {emotional_payoff}
COMMENT QUESTION: {comment_question}

SCRIPT EXCERPT:
{script[:1000]}

═══════════════════════════════════════════════
TITLE DIRECTIONS — Choose the one that best fits this script:
═══════════════════════════════════════════════

1. PARADOX:
   "Jesus Was Silent—But He Hadn't Left"

2. HUMAN QUESTION:
   "Why Did Jesus Weep If He Knew the Ending?"

3. OVERLOOKED DETAIL:
   "The Detail Everyone Misses in This Jesus Story"

4. PERSONAL REFRAME:
   "When God Feels Silent, Remember This Moment"

5. CONCRETE STORY TENSION:
   "Peter Was Sinking. Jesus Asked One Question"

RULES:
- Write the title for a scrolling viewer, not as a sermon heading.
- Keep it 38-58 characters and place the tension in the first 35 characters.
- Include one natural faith keyword such as Jesus, God, Bible, or Scripture.
- Open one curiosity gap and preserve the video's answer; do not summarize the whole lesson.
- Use concrete nouns and active verbs. Make the viewer feel personally implicated.
- Use title case, no ALL CAPS, no emoji, and at most one punctuation mark.
- Match this viral pattern: {topic_config.get('viral_pattern', 'human_crisis')}.
- Never use fabricated personal stories, fear, prophecy, guilt, or controversy.
- Never use generic bait such as "will give you chills", "you need to hear this",
  "watch before it's too late", "God is telling you", "this changes everything",
  "most Christians get this wrong", or "what churches won't tell you".

DESCRIPTION RULES:
- Start with a 7-12 word continuation of the hook, without giving away the revelation.
- In 2-3 short sentences, name the struggle, the passage, and the useful takeaway.
- End with the supplied honest reflection question, then 3-5 precise hashtags.
- Keep the full description between 250 and 450 characters.
- Do not repeat the title, keyword-stuff, preach at the viewer, or add unsupported claims.

SHORTS FIELD RULES:
- shorts_title is the same core title, tightened to fit 50 characters including #Shorts.
- shorts_description is 100-180 characters and retains the reflection question.

Return ONLY a valid JSON object:
{{
  "title": "Truthful, specific title following every rule above",
  "description": "Hook continuation, useful context, reflection question, then 3-5 hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15"],
  "shorts_title": "Core title plus #Shorts, 50 characters maximum",
  "shorts_description": "Concise description with reflection question and 3-4 hashtags"
}}"""

    try:
        raw = chat_complete(prompt, system=system, temperature=0.7, json_mode=True)
        metadata = extract_json(raw)

        # Merge tags
        all_tags = metadata.get("tags", [])
        combined_tags = list(dict.fromkeys(all_tags + BASE_TAGS))[:35]
        metadata["tags"] = combined_tags

        # Validate title length (40-60 chars optimal for Shorts)
        title = metadata.get("title", topic)
        if len(title) < 30 or len(title) > 70:
            logger.warning(f"Title length suboptimal ({len(title)} chars): {title[:50]}...")
        if len(title) > 100:
            metadata["title"] = title[:97] + "..."

        # Validate title has curiosity gap (not generic)
        boring_patterns = [
            "something about",
            "explained",
            "what is ",
            "how to ",
            "everything about",
            "the truth about",
            "you need to hear this",
            "will give you chills",
            "what churches won't tell you",
        ]
        if any(p in title.lower() for p in boring_patterns):
            logger.warning(f"Title may be too generic/boring: {title}")

        # Validate title contains primary keyword
        primary_kw = keywords[0] if keywords else "jesus"
        if primary_kw.lower() not in title.lower() and not any(kw in title.lower() for kw in ["god", "bible", "christ", "scripture", "faith"]):
            logger.warning(f"Title missing primary keyword '{primary_kw}': {title}")
            metadata["title"] = f"{title[:45]} | {primary_kw.title()}"

        logger.info(f"✅ SEO OK | Title: {metadata.get('title', '')[:55]}")
        return metadata

    except Exception as e:
        logger.warning(f"SEO generation failed, dùng fallback: {e}")
        return _fallback_metadata(topic_config)


def _fallback_metadata(topic_config: dict) -> dict:
    """Metadata cơ bản nếu API thất bại."""
    topic    = topic_config["topic"]
    keywords = topic_config.get("keywords", [])
    bible    = topic_config.get("bible_reference", "")

    title = f"{topic} | {CHANNEL_NAME}"[:100]
    kw    = keywords[0].title() if keywords else "Jesus"

    description = (
        f"✝️ {topic}\n\n"
        f"{bible} — Discover the power of God's Word in 60 seconds.\n\n"
        f"Follow @{CHANNEL_NAME} for daily Scripture and inspiration.\n\n"
        f"#Jesus #Bible #Christianity #Faith #Shorts"
    )

    tags = list(dict.fromkeys(keywords + BASE_TAGS))[:35]

    return {
        "title":              title,
        "description":        description,
        "tags":               tags,
        "shorts_title":       f"{topic[:45]} #Shorts",
        "shorts_description": f"✝️ {kw} in 60 seconds! {bible} #Shorts #Jesus #Bible #Faith",
    }


def format_description_for_youtube(description: str) -> str:
    """Format description phù hợp với YouTube."""
    desc = description.replace("\\n", "\n")
    desc = "\n".join(line.rstrip() for line in desc.split("\n"))
    return desc.strip()
