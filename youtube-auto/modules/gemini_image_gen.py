"""
==========================================================
  MODULE: GEMINI IMAGE GENERATOR (google-genai SDK mới)
  Tạo hình ảnh AI độc bản bằng Nano Banana (gemini-2.5-flash-image)
  - Free Tier: 500 requests/ngày, 10 requests/phút
  - Đây là model duy nhất hỗ trợ tạo ảnh MIỄN PHÍ (không cần Billing)
==========================================================
"""

import logging
import time
import os
from pathlib import Path
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, IMAGEN_MODEL

logger = logging.getLogger(__name__)


def _get_client():
    """Khởi tạo client từ thư viện google-genai mới."""
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_single_image(prompt: str, output_path: str | Path) -> bool:
    """
    Tạo một ảnh từ prompt bằng Nano Banana (gemini-2.5-flash-image).
    Sử dụng generate_content với response_modalities=['IMAGE'].
    """
    logger.info(f"Đang tạo ảnh AI: {prompt[:60]}...")

    client = _get_client()

    full_prompt = (
        f"{prompt}. "
        f"Cinematic quality, hyper-detailed, photorealistic, professional lighting, "
        f"sharp focus, high-resolution, masterpiece artwork."
    )

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=IMAGEN_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )

            # Duyệt qua các part để tìm dữ liệu ảnh
            for part in response.parts:
                if part.inline_data is not None:
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)

                    size_kb = os.path.getsize(output_path) / 1024
                    logger.info(f"✅ Ảnh AI đã lưu: {Path(output_path).name} ({size_kb:.1f} KB)")
                    return True

            # Có text response nhưng không có ảnh — thường do safety filter
            text_response = "".join(p.text for p in response.parts if p.text)
            if text_response:
                logger.warning(f"Lần {attempt+1}: Model chỉ trả text (không có ảnh): {text_response[:100]}")
            else:
                logger.warning(f"Lần {attempt+1}: Response trống, không có ảnh.")

        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"Lần {attempt+1} thất bại: {e}")

            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                # Lấy retry delay từ API nếu có
                wait_time = 65
                logger.info(f"⏳ Rate limit, chờ {wait_time}s...")
                time.sleep(wait_time)
                continue

            elif "invalid_argument" in err_str and "paid" in err_str:
                logger.error(
                    f"❌ Model '{IMAGEN_MODEL}' yêu cầu tài khoản trả phí.\n"
                    f"   Hãy đặt IMAGEN_MODEL='gemini-2.5-flash-image' trong config.py"
                )
                return False

            else:
                time.sleep(5)

    logger.error(f"❌ Không tạo được ảnh sau 4 lần thử: {prompt[:50]}")
    return False


def generate_shorts_images(
    scenes: list[dict],
    output_dir: str | Path,
    video_id: str = ""
) -> list[str]:
    """
    Tạo bộ ảnh cho toàn bộ phân cảnh (scenes) của một video.

    Args:
        scenes:     Danh sách dict [{'visual_prompt': '...', 'text': '...'}]
        output_dir: Thư mục lưu ảnh
        video_id:   ID video để đặt tên file

    Returns:
        Danh sách đường dẫn các ảnh đã tạo thành công.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_paths = []

    for i, scene in enumerate(scenes):
        prompt = scene.get("visual_prompt") or scene.get("text", "")
        if not prompt:
            logger.warning(f"Scene {i+1}: thiếu prompt, bỏ qua.")
            continue

        filename = f"{video_id}_scene_{i+1:02d}.png" if video_id else f"scene_{i+1:02d}.png"
        save_path = output_dir / filename

        # Bỏ qua nếu đã tạo rồi (resume khi bị ngắt)
        if save_path.exists() and save_path.stat().st_size > 5_000:
            logger.info(f"Scene {i+1}: ảnh đã tồn tại, bỏ qua.")
            downloaded_paths.append(str(save_path))
            continue

        logger.info(f"--- Scene {i+1}/{len(scenes)} ---")
        if generate_single_image(prompt, save_path):
            downloaded_paths.append(str(save_path))
        else:
            logger.error(f"Scene {i+1}: tạo ảnh thất bại → bỏ qua.")

        # Chờ giữa các requests để tránh rate limit (10 req/min)
        if i < len(scenes) - 1:
            time.sleep(7)

    logger.info(f"Tổng cộng: {len(downloaded_paths)}/{len(scenes)} ảnh được tạo thành công.")
    return downloaded_paths


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    test_scenes = [{"visual_prompt": "A dramatic sunset over a medieval cathedral, cinematic"}]
    out = generate_shorts_images(test_scenes, "output/test_nanobana")
    print(f"Result: {out}")
