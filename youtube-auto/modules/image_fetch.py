"""
==========================================================
  MODULE: IMAGE FETCHER
  Tải ảnh miễn phí từ Pexels + Pixabay (không bản quyền)
==========================================================
"""

import os
import time
import logging
import requests
from pathlib import Path
from config import PEXELS_API_KEY, PIXABAY_API_KEY

logger = logging.getLogger(__name__)

# Headers cho Pexels
PEXELS_HEADERS = {
    "Authorization": PEXELS_API_KEY,
    "User-Agent":    "YoutubeAutoPipeline/1.0"
}


# ============================================================
# PEXELS API
# ============================================================

def search_pexels(query: str, per_page: int = 8, orientation: str = "landscape") -> list[dict]:
    """
    Tìm kiếm ảnh trên Pexels.
    
    Args:
        query:       Từ khóa tìm kiếm
        per_page:    Số ảnh cần lấy (max 80)
        orientation: "landscape", "portrait", "square"
        
    Returns:
        Danh sách dict chứa URL ảnh
    """
    url = "https://api.pexels.com/v1/search"
    params = {
        "query":       query,
        "per_page":    per_page,
        "orientation": orientation,
        "size":        "large",      # "large" = min 1920px
    }
    try:
        response = requests.get(url, headers=PEXELS_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        photos = data.get("photos", [])
        results = []
        for p in photos:
            results.append({
                "url":         p["src"]["large2x"] or p["src"]["large"],
                "url_original":p["src"]["original"],
                "photographer":p.get("photographer", "Unknown"),
                "alt":         p.get("alt", ""),
                "source":      "pexels",
                "id":          p["id"],
            })
        logger.info(f"Pexels '{query}': tìm thấy {len(results)} ảnh")
        return results
    except Exception as e:
        logger.warning(f"Pexels lỗi cho '{query}': {e}")
        return []


# ============================================================
# PIXABAY API
# ============================================================

def search_pixabay(query: str, per_page: int = 8, image_type: str = "photo") -> list[dict]:
    """
    Tìm kiếm ảnh trên Pixabay.
    
    Args:
        query:      Từ khóa tìm kiếm
        per_page:   Số ảnh (max 200)
        image_type: "photo", "illustration", "vector"
        
    Returns:
        Danh sách dict chứa URL ảnh
    """
    url = "https://pixabay.com/api/"
    params = {
        "key":          PIXABAY_API_KEY,
        "q":            query,
        "per_page":     per_page,
        "image_type":   image_type,
        "orientation":  "horizontal",
        "min_width":    1280,
        "safesearch":   "true",
        "lang":         "en",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])
        results = []
        for h in hits:
            # Ưu tiên ảnh lớn nhất
            img_url = h.get("largeImageURL") or h.get("webformatURL")
            if img_url:
                results.append({
                    "url":         img_url,
                    "url_original":h.get("largeImageURL", img_url),
                    "photographer":h.get("user", "Unknown"),
                    "alt":         h.get("tags", ""),
                    "source":      "pixabay",
                    "id":          h["id"],
                })
        logger.info(f"Pixabay '{query}': tìm thấy {len(results)} ảnh")
        return results
    except Exception as e:
        logger.warning(f"Pixabay lỗi cho '{query}': {e}")
        return []


# ============================================================
# DOWNLOAD ẢNH
# ============================================================

def download_image(url: str, save_path: str | Path, timeout: int = 20) -> bool:
    """
    Tải và lưu một ảnh.
    
    Args:
        url:       URL ảnh cần tải
        save_path: Đường dẫn lưu file
        timeout:   Timeout request (giây)
        
    Returns:
        True nếu thành công, False nếu lỗi
    """
    try:
        headers = {"User-Agent": "YoutubeAutoPipeline/1.0"}
        response = requests.get(url, stream=True, timeout=timeout, headers=headers)
        response.raise_for_status()

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = save_path.stat().st_size / 1024
        if size_kb < 5:  # Ảnh quá nhỏ = có thể lỗi
            save_path.unlink()
            logger.warning(f"Ảnh quá nhỏ, bỏ qua: {url}")
            return False

        logger.debug(f"Tải ảnh OK: {save_path.name} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        logger.warning(f"Lỗi tải ảnh {url}: {e}")
        return False


# ============================================================
# FETCH NHIỀU ẢNH THEO TOPIC
# ============================================================

def fetch_images_for_topic(
    topic_config: dict,
    output_dir: str | Path,
    max_images: int = 10,
    video_id: str   = ""
) -> list[str]:
    """
    Tải ảnh phù hợp với chủ đề video.
    Tự động thử nhiều từ khóa và kết hợp Pexels + Pixabay.
    
    Args:
        topic_config: Dict từ RELIGION_TOPICS
        output_dir:   Thư mục lưu ảnh
        max_images:   Số ảnh tối đa
        video_id:     ID để đặt tên file
        
    Returns:
        Danh sách đường dẫn file ảnh đã tải
    """
    keywords   = topic_config.get("keywords", [])
    religion   = topic_config.get("religion", "world")
    output_dir = Path(output_dir)

    # Xây dựng danh sách query từ keywords
    # Ưu tiên query tổng hợp trước, rồi từng keyword riêng
    queries = []
    if keywords:
        # Query tổng hợp
        queries.append(f"{religion.lower()} {keywords[0]}")
        # Từng keyword riêng
        for kw in keywords[1:]:
            queries.append(kw)
    queries += ["spiritual meditation", "sacred temple", "religious ceremony", "prayer faith"]

    # Ảnh fallback phổ biến nếu không tìm được
    fallback_queries = ["nature peaceful", "sunrise landscape", "ancient architecture"]

    collected = []   # (url, source, query)
    seen_ids  = set()

    def _collect_from_api(q: str, needed: int):
        nonlocal collected
        if len(collected) >= needed:
            return
        # Thử Pexels trước
        pexels_res = search_pexels(q, per_page=min(needed, 6))
        for item in pexels_res:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                collected.append(item)
        time.sleep(0.3)  # Tránh rate limit

        # Nếu chưa đủ thì dùng Pixabay
        if len(collected) < needed:
            pixabay_res = search_pixabay(q, per_page=min(needed, 6))
            for item in pixabay_res:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    collected.append(item)
            time.sleep(0.3)

    # Thu thập ảnh từ queries chính
    for q in queries:
        _collect_from_api(q, max_images)
        if len(collected) >= max_images:
            break

    # Nếu vẫn thiếu, dùng fallback
    if len(collected) < max_images // 2:
        logger.warning("Thiếu ảnh, dùng fallback queries...")
        for q in fallback_queries:
            _collect_from_api(q, max_images)
            if len(collected) >= max_images:
                break

    # Giới hạn số ảnh và tải về
    collected = collected[:max_images]
    downloaded_paths = []

    for i, item in enumerate(collected):
        ext  = ".jpg"
        name = f"{video_id}_img_{i+1:02d}{ext}" if video_id else f"img_{i+1:02d}{ext}"
        save_path = output_dir / name

        if download_image(item["url"], save_path):
            downloaded_paths.append(str(save_path))
        else:
            # Thử URL gốc nếu URL đầu hỏng
            if item.get("url_original") and item["url_original"] != item["url"]:
                if download_image(item["url_original"], save_path):
                    downloaded_paths.append(str(save_path))

    logger.info(f"Đã tải {len(downloaded_paths)}/{max_images} ảnh vào {output_dir}")
    return downloaded_paths
