"""
==========================================================
  MODULE: SEO OPTIMIZER (NEW SDK - BULLETPROOF JSON)
  Dùng Gemini (google-genai) để tạo title, description, tags tối ưu SEO
==========================================================
"""

import logging
import json
import time
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, BASE_TAGS, CHANNEL_NAME

logger = logging.getLogger(__name__)

# --- Định nghĩa cấu hình dữ liệu SEO bằng Pydantic ---
class SEOMetadata(BaseModel):
    title: str = Field(description="Video title, 60-70 chars, must include primary keyword, add emotional hook.")
    description: str = Field(description="Full YouTube description, 800-1000 characters with timestamps and hashtags.")
    tags: list[str] = Field(description="List of 30 highly relevant tags (lowercase, phrases).")
    shorts_title: str = Field(description="YouTube Shorts title, max 50 chars, ends with #Shorts.")
    shorts_description: str = Field(description="Shorts description, 200-300 chars, with 3-4 hashtags.")

def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)

def generate_seo_metadata(
    topic_config: dict,
    script: str,
) -> dict:
    """
    Tạo SEO metadata sử dụng JSON Mode của google-genai SDK.
    Đảm bảo kết quả trả về luôn là JSON hợp lệ 100%.
    """
    topic    = topic_config["topic"]
    religion = topic_config["religion"]
    keywords = topic_config.get("keywords", [])

    logger.info("Đang tạo SEO metadata (JSON Mode)...")

    client = _get_client()

    # Model cho SEO không cần Imagen, dùng Flash 2.0 là tốt nhất cho tốc độ và JSON
    # Nếu gemini-2.0-flash không có sẵn, dùng gemini-1.5-flash
    model_id = "gemini-2.0-flash" 

    prompt = f"""You are a YouTube SEO expert specializing in religious and spiritual content.
Generate comprehensive SEO metadata for a YouTube video.

VIDEO TOPIC: {topic}
RELIGION: {religion}
PRIMARY KEYWORDS: {', '.join(keywords)}
CHANNEL: {CHANNEL_NAME}

SCRIPT EXCERPT:
{script[:2000]}

INSTRUCTIONS:
- Title MUST start with the primary keyword.
- Description must include line breaks (\\n) and timestamps (0:00 - Intro, etc.).
- Include exactly 30 relevant tags.
- Shorts title must end with #Shorts.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_json_schema=SEOMetadata.model_json_schema(),
                    temperature=0.7,
                )
            )

            # Với SDK này và JSON mode, response.text sẽ là chuỗi JSON sạch
            raw_json = response.text.strip()
            metadata_dict = json.loads(raw_json)

            # Hậu xử lý: Merge tags với BASE_TAGS
            all_tags = metadata_dict.get("tags", [])
            combined_tags = list(dict.fromkeys(all_tags + BASE_TAGS))[:35]
            metadata_dict["tags"] = combined_tags

            # Validate title length
            title = metadata_dict.get("title", topic)
            if len(title) > 100:
                metadata_dict["title"] = title[:97] + "..."

            logger.info(f"✅ SEO Metadata OK | Title: {metadata_dict.get('title')[:50]}...")
            return metadata_dict

        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"SEO attempt {attempt+1} lỗi: {err_str}")
            
            # Fallback model nếu gemini-2.0-flash chưa khả dụng hoặc hết quota
            if ("not_found" in err_str or "quota" in err_str or "exhausted" in err_str) and model_id == "gemini-2.0-flash":
                logger.info("🔄 Chuyển sang model fallback gemini-2.5-flash...")
                model_id = "gemini-2.5-flash"
                continue

            if attempt < 2:
                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    logger.info("⏳ Quá tải API, chờ 30s...")
                    time.sleep(30)
                else:
                    time.sleep(5)

    # Fallback cuối cùng nếu AI hoàn toàn thất bại
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
    """Format description phù hợp với YouTube."""
    # Với SDK mới, chuỗi thường đã chứa \n thật, không cần replace \\n trừ khi model vẫn làm vậy
    desc = description.replace("\\n", "\n")
    desc = "\n".join(line.rstrip() for line in desc.split("\n"))
    return desc.strip()
