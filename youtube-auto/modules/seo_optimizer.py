"""
==========================================================
  MODULE: SEO OPTIMIZER
  Dùng Gemini để tạo title, description, tags tối ưu SEO
==========================================================
"""

import logging
import re
import time
import json
import google.generativeai as genai
from config import GEMINI_API_KEY, BASE_TAGS, CHANNEL_NAME

logger = logging.getLogger(__name__)


def _configure_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.5-flash")


def generate_seo_metadata(
    topic_config: dict,
    script: str,
) -> dict:
    """
    Tạo toàn bộ SEO metadata cho video YouTube.

    Args:
        topic_config: Dict từ RELIGION_TOPICS
        script:       Script đã tạo (để Gemini phân tích nội dung)
        
    Returns:
        Dict chứa: title, description, tags, shorts_title, shorts_description
    """
    topic    = topic_config["topic"]
    religion = topic_config["religion"]
    keywords = topic_config.get("keywords", [])

    logger.info("Đang tạo SEO metadata...")

    model = _configure_gemini()

    prompt = f"""You are a YouTube SEO expert specializing in religious and spiritual content.

Generate comprehensive SEO metadata for a YouTube video.

VIDEO TOPIC: {topic}
RELIGION: {religion}
PRIMARY KEYWORDS: {', '.join(keywords)}
CHANNEL: {CHANNEL_NAME}

SCRIPT EXCERPT (first 400 words):
{script[:1600]}

Please generate the following in JSON format:

{{
  "title": "Exact video title, 60-70 chars, must include primary keyword, add emotional hook like 'That Will...' or '...You Never Knew'. MUST start with keyword.",
  "description": "Full YouTube description, 800-1000 characters. Format:\\n\\n- First 2 sentences: hook that compels people to watch (shows in search results)\\n- Brief overview of what video covers (4-5 sentences)\\n- Time-stamped sections: 0:00 - Intro\\n0:30 - [Topic 1]\\n[etc.]\\n- 3-4 relevant hashtags at end (#Religion #Spiritual etc.)\\n- End with Subscribe CTA",
  "tags": ["list", "of", "30", "highly", "relevant", "tags", "mix", "of", "broad", "and", "niche", "keywords", "include", "long-tail", "phrases"],
  "shorts_title": "YouTube Shorts title, 40-50 chars, add #Shorts at end",
  "shorts_description": "Shorts description, 200-300 chars, 3-4 hashtags"
}}

IMPORTANT:
- Title must NOT start with articles (A, The, An)
- Tags should be lowercase, mix of 1-word and multi-word phrases
- Include EXACTLY 30 tags
- Description must be formatted with line breaks (use \\n)
- Do NOT include markdown, return clean JSON only"""

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1500,
                    response_mime_type="application/json"
                )
            )

            raw = response.text.strip() if response.text else ""

            # Xóa các markdown block trong trường hợp Gemini vẫn trả về dù dùng JSON mode
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                raw = json_match.group()
                
            if not raw:
                raise ValueError("Empty response or no JSON found")

            try:
                metadata = json.loads(raw)
            except json.JSONDecodeError as e:
                # Xử lý an toàn hơn khi parse do chuỗi có thể chứa \n \t không escape
                metadata = json.loads(raw, strict=False)

            # Merge tags với BASE_TAGS và dedup
            all_tags = metadata.get("tags", [])
            combined = list(dict.fromkeys(all_tags + BASE_TAGS))[:35]
            metadata["tags"] = combined

            # Validate title length
            title = metadata.get("title", topic)
            if len(title) > 100:
                metadata["title"] = title[:97] + "..."

            logger.info(f"SEO metadata OK | Title: {metadata.get('title', '')[:50]}...")
            return metadata

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse lỗi attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(3)
        except Exception as e:
            logger.warning(f"SEO attempt {attempt+1} lỗi: {e}")
            if attempt < 2:
                time.sleep(5)

    # Fallback: tạo metadata cơ bản nếu Gemini thất bại
    logger.warning("Dùng SEO metadata fallback")
    return _fallback_metadata(topic_config)


def _fallback_metadata(topic_config: dict) -> dict:
    """Tạo metadata cơ bản nếu Gemini API thất bại."""
    topic    = topic_config["topic"]
    religion = topic_config["religion"]
    keywords = topic_config.get("keywords", [])

    title = f"{topic} | {CHANNEL_NAME}"[:100]

    keyword_str = ", ".join(keywords[:5])
    description = (
        f"Explore the fascinating world of {religion} in this eye-opening video about {topic}.\n\n"
        f"In this video, we dive deep into {keyword_str} and discover timeless wisdom "
        f"that applies to modern life. Whether you're religious or simply curious about spirituality, "
        f"this video will inspire and enlighten you.\n\n"
        f"📌 TIMESTAMPS:\n"
        f"0:00 - Introduction\n"
        f"1:00 - Historical Background\n"
        f"3:00 - Key Teachings\n"
        f"6:00 - Modern Applications\n"
        f"8:00 - Conclusion\n\n"
        f"👍 Like, Subscribe & Share if this video moved you!\n\n"
        f"#{religion.lower()} #{keywords[0].replace(' ', '')} #spiritual #wisdom #sacredwisdom"
    )

    tags = list(dict.fromkeys(keywords + BASE_TAGS))[:35]
    shorts_title = f"{topic[:45]}... #Shorts"

    return {
        "title":              title,
        "description":        description,
        "tags":               tags,
        "shorts_title":       shorts_title,
        "shorts_description": f"Discover amazing {religion} wisdom! {keywords[0].title()} explained in 60 seconds. #Shorts #{religion.lower()} #spiritual",
    }


def format_description_for_youtube(description: str) -> str:
    """Format description phù hợp với YouTube (xử lý escape chars)."""
    # Chuyển \\n thành newline thật
    desc = description.replace("\\n", "\n")
    # Trim whitespace thừa
    desc = "\n".join(line.rstrip() for line in desc.split("\n"))
    return desc.strip()
