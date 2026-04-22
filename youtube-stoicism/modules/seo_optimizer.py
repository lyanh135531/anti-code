"""
==========================================================
  MODULE: SEO OPTIMIZER (Pollinations AI)
  Tạo title, description, tags tối ưu SEO cho YouTube Shorts.
  Dùng Pollinations AI — không bị 429 quota!
==========================================================
"""

import logging
import json
from modules.pollinations_text import chat_complete, extract_json
from config import BASE_TAGS, CHANNEL_NAME

logger = logging.getLogger(__name__)


def generate_seo_metadata(topic_config: dict, script: str) -> dict:
    """
    Tạo SEO metadata cho YouTube Shorts bằng Pollinations AI.
    """
    topic    = topic_config["topic"]
    keywords = topic_config.get("keywords", [])
    bible    = topic_config.get("bible_reference", "")

    logger.info("Đang tạo SEO metadata (Pollinations)...")

    system = (
        "You are a YouTube SEO expert specializing in Christian faith content. "
        "You write compelling titles and descriptions that maximize click-through rates "
        "for a Shorts channel dedicated to Jesus Christ and the Bible."
    )

    prompt = f"""Generate SEO metadata for a YouTube Shorts video about Jesus Christ.

VIDEO TOPIC: {topic}
BIBLE REFERENCE: {bible}
PRIMARY KEYWORDS: {', '.join(keywords)}
CHANNEL: {CHANNEL_NAME}

SCRIPT EXCERPT:
{script[:1000]}

Return ONLY a valid JSON object:
{{
  "title": "Compelling Shorts title, 50-70 chars, include primary keyword and emotional hook",
  "description": "YouTube description, 400-600 chars, with 3-5 relevant hashtags at end",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15"],
  "shorts_title": "Shorts title max 50 chars #Shorts",
  "shorts_description": "Short description 100-200 chars with 3-4 hashtags #Shorts #Jesus #Bible"
}}"""

    try:
        raw = chat_complete(prompt, system=system, temperature=0.7, json_mode=True)
        metadata = extract_json(raw)

        # Merge tags
        all_tags = metadata.get("tags", [])
        combined_tags = list(dict.fromkeys(all_tags + BASE_TAGS))[:35]
        metadata["tags"] = combined_tags

        # Validate title length
        title = metadata.get("title", topic)
        if len(title) > 100:
            metadata["title"] = title[:97] + "..."

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
