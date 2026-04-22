"""
==========================================================
  MODULE: POLLINATIONS IMAGE GENERATOR
  Tạo hình ảnh AI bằng Pollinations.ai (Flux-Schnell)
  - Phù hợp với tài khoản có Pollen balance
==========================================================
"""

import logging
import time
import os
import urllib.parse
import requests
from pathlib import Path
from config import POLLINATIONS_API_KEY, AI_IMAGE_MODEL

logger = logging.getLogger(__name__)


def generate_single_image(prompt: str, output_path: str | Path, width: int = 1080, height: int = 1920) -> bool:
    """
    Tạo một ảnh từ prompt bằng Pollinations API.
    Sử dụng model được cấu hình (ví dụ: flux-schnell).
    """
    # Style suffix: có thể dùng anime/painting style để tránh lỗi gương mặt
    STYLE_SUFFIX = (
        "cinematic digital painting, anime art style, Studio Ghibli-inspired, "
        "warm golden lighting, rich colors, no ugly faces, beautiful scenery"
    )
    NEGATIVE_PROMPT = (
        "realistic face, photorealistic, ugly face, deformed face, distorted face, "
        "bad anatomy, extra limbs, blurry, low quality, watermark, text, signature"
    )

    logger.info(f"Đang tạo ảnh bằng Pollinations ({AI_IMAGE_MODEL}): {prompt[:60]}...")

    full_prompt = f"{prompt}, {STYLE_SUFFIX}"
    encoded_prompt = urllib.parse.quote(full_prompt)
    encoded_negative = urllib.parse.quote(NEGATIVE_PROMPT)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&model={AI_IMAGE_MODEL}&nologo=true"
        f"&negative_prompt={encoded_negative}&enhance=false&safe=false"
    )

    headers = {}
    if POLLINATIONS_API_KEY and POLLINATIONS_API_KEY != "YOUR_POLLINATIONS_API_KEY":
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
    else:
        logger.warning("POLLINATIONS_API_KEY chưa được đặt. Yêu cầu có thể bị từ chối hoặc trả về lỗi 401.")

    output_path = Path(output_path)
    # Tạo thư mục cha nếu chưa có
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(4):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                size_kb = os.path.getsize(output_path) / 1024
                if size_kb < 10:
                    logger.warning(f"Lần {attempt+1}: Ảnh trả về quá nhỏ ({size_kb:.1f} KB). Có thể lỗi API.")
                    if attempt < 3:
                        time.sleep(5)
                        continue
                    return False
                
                logger.info(f"✅ Ảnh đã lưu: {output_path.name} ({size_kb:.1f} KB)")
                return True
                
            elif response.status_code in [401, 403]:
                logger.error(f"❌ Lỗi {response.status_code}: Pollinations từ chối yêu cầu. Kiểm tra lại POLLINATIONS_API_KEY và số dư Pollen của bạn.")
                return False
                
            elif response.status_code == 429:
                wait_time = 15
                logger.info(f"⏳ Rate limit từ Pollinations, chờ {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            else:
                logger.warning(f"Lần {attempt+1} thất bại: HTTP {response.status_code}")
                time.sleep(5)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Lần {attempt+1} lỗi mạng: {e}")
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
    Dành riêng cho Shorts nên chiều dọc (1080x1920).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_paths = []

    for i, scene in enumerate(scenes):
        prompt = scene.get("visual_prompt") or scene.get("text", "")
        if not prompt:
            logger.warning(f"Scene {i+1}: thiếu prompt, bỏ qua.")
            continue

        filename = f"{video_id}_scene_{i+1:02d}.jpg" if video_id else f"scene_{i+1:02d}.jpg"
        save_path = output_dir / filename

        # Bỏ qua nếu đã tạo rồi (resume khi bị ngắt)
        if save_path.exists() and save_path.stat().st_size > 5_000:
            logger.info(f"Scene {i+1}: ảnh đã tồn tại, bỏ qua.")
            downloaded_paths.append(str(save_path))
            continue

        logger.info(f"--- Scene {i+1}/{len(scenes)} ---")
        # Shorts images use portrait orientation
        # Let's check aspect ratio. Since the original used Imagen which defaults to square or portrait,
        # here we'll explicitly pass width=1080, height=1920 (or square for long videos? The pipeline uses shorts format often. Let's do 1024x1024 for standard, and for shorts it should be portrait)
        # Actually in main.py, it uses `generate_shorts_images` for both main and shorts. Wait, no. main.py has `generate_shorts_images(main_scenes)`. Wait, it's called shorts_images everywhere?
        # Let's inspect main.py to see how `generate_shorts_images` is used. I'll just keep the default 1024x1024 for safety, or 1080x1920.
        # Let's use 1024x1024 as default for AI gen. Pollinations handles up to 1024 safely.
        
        if generate_single_image(prompt, save_path, width=768, height=1344):
            downloaded_paths.append(str(save_path))
        else:
            logger.error(f"Scene {i+1}: tạo ảnh thất bại → bỏ qua.")

        # Nghỉ nhẹ giữa các req để tránh trigger rate limit của API (Pollinations có thể giới hạn Req/s)
        if i < len(scenes) - 1:
            time.sleep(2)

    logger.info(f"Tổng cộng: {len(downloaded_paths)}/{len(scenes)} ảnh được tạo thành công.")
    return downloaded_paths


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    test_scenes = [{"visual_prompt": "A cinematic close-up of a single candle flickering in a vast dark cathedral"}]
    out = generate_shorts_images(test_scenes, "output/test_poll")
    print(f"Result: {out}")
