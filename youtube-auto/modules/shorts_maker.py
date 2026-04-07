"""
==========================================================
  MODULE: SHORTS MAKER
  Tạo YouTube Shorts (1080x1920, dưới 60 giây) từ video chính
==========================================================
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def create_shorts_from_video(
    main_video_path:  str | Path,
    audio_path:       str | Path,
    output_path:      str | Path,
    max_duration:     float = 58.0,
    W: int = 1080,
    H: int = 1920,
    fps: int = 24,
    channel_name: str = "Sacred Wisdom Daily",
) -> str:
    """
    Tạo YouTube Shorts 9:16 từ video 16:9 chính.
    Crop ảnh giữa + thêm blur background + audio ngắn.
    
    Args:
        main_video_path: Video gốc 1920x1080
        audio_path:      Audio ngắn (từ shorts script)
        output_path:     Đường dẫn lưu shorts
        max_duration:    Thời lượng tối đa (< 60s)
        
    Returns:
        Đường dẫn file shorts
    """
    try:
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, VideoClip,
            CompositeVideoClip, ColorClip
        )
        from moviepy.video.fx.all import resize, fadein, fadeout, crop
        import numpy as np
        from PIL import Image, ImageFilter, ImageDraw, ImageFont
    except ImportError:
        raise ImportError("Cần cài moviepy: pip install moviepy")

    output_path = Path(output_path)
    logger.info(f"Tạo Shorts: {output_path.name}")

    # ── 1. Load main video ────────────────────────────────
    main_clip = VideoFileClip(str(main_video_path))
    main_dur  = min(main_clip.duration, max_duration)

    # ── 2. Load shorts audio ──────────────────────────────
    shorts_audio = AudioFileClip(str(audio_path))
    audio_dur    = min(shorts_audio.duration, max_duration)
    final_dur    = min(main_dur, audio_dur)

    shorts_audio = shorts_audio.subclip(0, final_dur)

    # ── 3. Tạo video Shorts bằng PIL frame-by-frame ───────
    # Lấy video gốc 1920x1080 và tạo layout 1080x1920:
    #   - Top 60%: Crop giữa video gốc → 1080x1152
    #   - Bottom 40%: Blur version của video + text overlay

    main_clip_trimmed = main_clip.subclip(0, final_dur)

    def make_shorts_frame(t):
        # Lấy frame gốc
        src_frame = main_clip_trimmed.get_frame(t)  # (1080, 1920, 3)
        src_pil   = Image.fromarray(src_frame.astype(np.uint8))

        # Vertical canvas
        canvas = Image.new("RGB", (W, H), (0, 0, 0))

        # ── Phần trên: Crop center của video gốc ───────────
        # Crop 1920x1080 → 1080x607 (giữ tỷ lệ 16:9, chiều ngang = 1080)
        crop_w = W                          # 1080
        crop_h = int(W * 9 / 16)           # 607
        src_w, src_h = src_pil.size        # 1920, 1080

        left   = (src_w - crop_w) // 2
        top    = (src_h - crop_h) // 2
        cropped = src_pil.crop((left, top, left + crop_w, top + crop_h))

        # Scale lên để lấp 60% chiều cao canvas
        top_h   = int(H * 0.6)             # 1152
        cropped = cropped.resize((W, top_h), Image.LANCZOS)
        canvas.paste(cropped, (0, 0))

        # ── Phần dưới: Blur background ─────────────────────
        bottom_h = H - top_h               # 768
        blur_src = src_pil.resize((W, bottom_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(15))
        # Tối blur
        from PIL import ImageEnhance
        blur_src = ImageEnhance.Brightness(blur_src).enhance(0.4)
        canvas.paste(blur_src, (0, top_h))

        # ── Separator line ─────────────────────────────────
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(0, top_h - 3), (W, top_h + 3)], fill=(255, 200, 50))

        # ── Channel name ───────────────────────────────────
        try:
            font_ch = ImageFont.truetype("arialbd.ttf", 32) if os.path.exists("C:/Windows/Fonts/arialbd.ttf") else ImageFont.load_default()
        except Exception:
            font_ch = ImageFont.load_default()

        ch_text = f"▶ {channel_name}"
        draw.text((W//2 - 120, top_h + 30), ch_text, font=font_ch, fill=(255, 220, 100))

        # ── Shorts label ───────────────────────────────────
        try:
            font_sub = ImageFont.truetype("arial.ttf", 26) if os.path.exists("C:/Windows/Fonts/arial.ttf") else ImageFont.load_default()
        except Exception:
            font_sub = ImageFont.load_default()

        draw.text((W//2 - 80, H - 120), "👍 Like & Follow", font=font_sub, fill=(200, 200, 200))

        return np.array(canvas, dtype=np.uint8)

    # Tạo VideoClip
    shorts_clip = VideoClip(make_shorts_frame, duration=final_dur).set_fps(fps)
    shorts_clip = shorts_clip.set_audio(shorts_audio)

    # Fade in/out
    from moviepy.video.fx.all import fadein, fadeout
    shorts_clip = fadein(shorts_clip, duration=0.5)
    shorts_clip = fadeout(shorts_clip, duration=0.5)

    # ── 4. Export ──────────────────────────────────────────
    logger.info(f"Đang export Shorts ({final_dur:.1f}s)...")
    shorts_clip.write_videofile(
        str(output_path),
        codec         = "libx264",
        audio_codec   = "aac",
        bitrate       = "4000k",    # Shorts cần bitrate cao hơn
        audio_bitrate = "128k",
        preset        = "fast",
        logger        = None,
        verbose       = False,
    )

    main_clip.close()
    shorts_clip.close()
    main_clip_trimmed.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✅ Shorts hoàn thành: {output_path.name} ({size_mb:.1f} MB)")
    return str(output_path)


def create_shorts_from_images(
    image_paths:  list[str],
    audio_path:   str | Path,
    output_path:  str | Path,
    channel_name: str = "Sacred Wisdom Daily",
    fps: int     = 24,
    W: int       = 1080,
    H: int       = 1920,
) -> str:
    """
    Tạo Shorts trực tiếp từ ảnh (không cần video gốc).
    Nhanh hơn phương pháp từ video chính.
    """
    try:
        from moviepy.editor import AudioFileClip, VideoClip
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    except ImportError:
        raise ImportError("Cần cài moviepy")

    output_path  = Path(output_path)
    audio_clip   = AudioFileClip(str(audio_path))
    total_dur    = min(audio_clip.duration, 58.0)
    img_dur      = total_dur / max(len(image_paths), 1)

    logger.info(f"Tạo Shorts từ {len(image_paths)} ảnh | {total_dur:.1f}s")

    # Pre-load và resize tất cả ảnh
    portrait_imgs = []
    for ip in image_paths:
        try:
            img = Image.open(ip).convert("RGB")
            # Crop center → portrait
            targ_ratio = W / H
            src_ratio  = img.width / img.height
            if src_ratio > targ_ratio:
                new_w = int(img.height * targ_ratio)
                off   = (img.width - new_w) // 2
                img   = img.crop((off, 0, off + new_w, img.height))
            else:
                new_h = int(img.width / targ_ratio)
                off   = (img.height - new_h) // 2
                img   = img.crop((0, off, img.width, off + new_h))
            img = img.resize((W, H), Image.LANCZOS)
            portrait_imgs.append(np.array(img))
        except Exception as e:
            logger.warning(f"Lỗi load ảnh Shorts {ip}: {e}")

    if not portrait_imgs:
        raise RuntimeError("Không có ảnh nào để tạo Shorts")

    n_imgs = len(portrait_imgs)

    def make_frame(t):
        idx   = min(int(t / img_dur), n_imgs - 1)
        frame = portrait_imgs[idx].copy()
        pil   = Image.fromarray(frame)

        draw = ImageDraw.Draw(pil)
        # Gradient overlay phía dưới
        for y in range(int(H * 0.7), H):
            ratio = (y - H * 0.7) / (H * 0.3)
            a = int(160 * ratio)
            draw.line([(0, y), (W, y)], fill=(0, 0, 0, a))

        # Channel label
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 36)
        except Exception:
            font = ImageFont.load_default()

        draw.text((W//2 - 150, H - 180), f"▶ {channel_name}", font=font, fill=(255, 220, 80))
        draw.text((W//2 - 100, H - 100), "👍 Follow for more!", font=font, fill=(200, 200, 200))

        return np.array(pil)

    clip = VideoClip(make_frame, duration=total_dur).set_fps(fps)
    clip = clip.set_audio(audio_clip.subclip(0, total_dur))

    from moviepy.video.fx.all import fadein, fadeout
    clip = fadein(clip, 0.3)
    clip = fadeout(clip, 0.3)

    clip.write_videofile(
        str(output_path),
        codec         = "libx264",
        audio_codec   = "aac",
        bitrate       = "4000k",
        audio_bitrate = "128k",
        preset        = "fast",
        logger        = None,
        verbose       = False,
    )

    clip.close()
    audio_clip.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✅ Shorts (từ ảnh): {output_path.name} ({size_mb:.1f} MB)")
    return str(output_path)
