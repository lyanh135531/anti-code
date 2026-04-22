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
        from moviepy import (
            VideoFileClip, AudioFileClip, VideoClip,
            CompositeVideoClip, ColorClip, vfx
        )
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

    shorts_audio = shorts_audio.subclipped(0, final_dur)

    # ── 3. Tạo video Shorts bằng PIL frame-by-frame ───────
    # Lấy video gốc 1920x1080 và tạo layout 1080x1920:
    #   - Top 60%: Crop giữa video gốc → 1080x1152
    #   - Bottom 40%: Blur version của video + text overlay

    main_clip_trimmed = main_clip.subclipped(0, final_dur)

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
        from config import FONTS_DIR
        font_ch_path = FONTS_DIR / "arialbd.ttf"
        try:
            if font_ch_path.exists():
                font_ch = ImageFont.truetype(str(font_ch_path), 32)
            elif os.name == 'nt' and os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                font_ch = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 32)
            else:
                font_ch = ImageFont.load_default()
        except Exception:
            font_ch = ImageFont.load_default()

        ch_text = f"| {channel_name}"
        draw.text((W//2 - 120, top_h + 30), ch_text, font=font_ch, fill=(255, 220, 100))

        # ── Shorts label ───────────────────────────────────
        font_sub_path = FONTS_DIR / "arial.ttf"
        try:
            if font_sub_path.exists():
                font_sub = ImageFont.truetype(str(font_sub_path), 26)
            elif os.name == 'nt' and os.path.exists("C:/Windows/Fonts/arial.ttf"):
                font_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
            else:
                font_sub = ImageFont.load_default()
        except Exception:
            font_sub = ImageFont.load_default()

        draw.text((W//2 - 80, H - 120), "👍 Like & Follow", font=font_sub, fill=(200, 200, 200))

        return np.array(canvas, dtype=np.uint8)

    # Tạo VideoClip
    shorts_clip = VideoClip(make_shorts_frame, duration=final_dur).with_fps(fps)
    shorts_clip = shorts_clip.with_audio(shorts_audio)

    # Fade in/out
    shorts_clip = shorts_clip.with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])

    # ── 4. Export ──────────────────────────────────────────
    logger.info(f"Đang export Shorts ({final_dur:.1f}s)...")
    shorts_clip.write_videofile(
        str(output_path),
        codec         = "libx264",
        audio_codec   = "aac",
        bitrate       = "4000k",    # Shorts cần bitrate cao hơn
        audio_bitrate = "128k",
        preset        = "fast",
        logger        = None
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
    channel_name: str = "Sacred Wisdom",
    fps: int     = 24,
    W: int       = 1080,
    H: int       = 1920,
    vtt_path:    str = None,
    music_path:  str = None,
) -> str:
    """
    Tạo Shorts chuyên nghiệp từ ảnh AI.
    - Hiệu ứng Ken Burns (zoom chậm)
    - Phụ đề trung tâm, cụm 3-4 từ
    - Không logo, tập trung thị trường quốc tế (Anh)
    """
    try:
        from moviepy import AudioFileClip, VideoClip, vfx
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    except ImportError:
        raise ImportError("Cần cài moviepy")

    output_path  = Path(output_path)
    audio_clip   = AudioFileClip(str(audio_path))
    total_dur    = min(audio_clip.duration, 59.0)
    
    final_audio = audio_clip.subclipped(0, total_dur)
    
    if music_path and os.path.exists(music_path):
        try:
            try:
                from moviepy.editor import CompositeAudioClip
            except ImportError:
                from moviepy import CompositeAudioClip
            bg_music = AudioFileClip(str(music_path))
            if bg_music.duration >= total_dur:
                bg_music = bg_music.subclipped(0, total_dur)
            
            try:
                bg_music = bg_music.volumex(0.12)
            except AttributeError:
                bg_music = bg_music.with_volume_scaled(0.12)
                
            try:
                bg_music = bg_music.set_start(0)
            except AttributeError:
                bg_music = bg_music.with_start(0)
                
            final_audio = CompositeAudioClip([final_audio, bg_music])
            logger.info(f"Đã trộn nhạc nền: {Path(music_path).name}")
        except Exception as e:
            logger.warning(f"Lỗi trộn nhạc nền: {e}")
            
    # Tính thời lượng mỗi ảnh
    n_imgs = len(image_paths)
    img_dur = total_dur / n_imgs if n_imgs > 0 else 5.0

    logger.info(f"Dựng Shorts AI: {n_imgs} ảnh | {total_dur:.1f}s")

    # Xử lý Subtitles: Nhóm 3-4 từ
    subs = []
    if vtt_path and os.path.exists(vtt_path):
        from modules.video_maker import parse_vtt, group_subs
        raw_subs = parse_vtt(str(vtt_path))
        subs = group_subs(raw_subs, max_words=4) 
        logger.info(f"Đã nạp {len(subs)} cụm phụ đề.")

    # Pre-load và scale ảnh (Portrait)
    # Chúng ta lấy ảnh to hơn 1 chút để có không gian zoom
    scaled_imgs = []
    for ip in image_paths:
        try:
            img = Image.open(ip).convert("RGB")
            # Crop center → portrait 
            target_ratio = W / H
            src_ratio = img.width / img.height
            if src_ratio > target_ratio:
                new_w = int(img.height * target_ratio)
                off = (img.width - new_w) // 2
                img = img.crop((off, 0, off + new_w, img.height))
            else:
                new_h = int(img.width / target_ratio)
                off = (img.height - new_h) // 2
                img = img.crop((0, off, img.width, off + new_h))
            
            # Phóng to 20% để lấy chỗ cho Ken Burns
            img = img.resize((int(W * 1.2), int(H * 1.2)), Image.LANCZOS)
            scaled_imgs.append(np.array(img))
        except Exception as e:
            logger.warning(f"Lỗi load ảnh {ip}: {e}")

    if not scaled_imgs:
        raise RuntimeError("Không có ảnh hợp lệ")

    directions = ["in", "out"] * (len(scaled_imgs) // 2 + 1)

    def _add_phrase_subtitle(pil_img, text, W, H):
        """
        Vẽ phụ đề Shorts chuẩn:
        - Vị trí: ~75% chiều cao (phía dưới, tránh UI YouTube)
        - Font: Bold 90px, chữ HOA
        - Nền: Box tối mờ (semi-transparent) để luôn dễ đọc
        - Màu chữ: Trắng với viền đen
        """
        import textwrap
        from PIL import ImageFont, ImageDraw, Image as PILImage

        # Tách dòng nếu text quá dài (tối đa 18 ký tự/dòng cho portrait)
        text = text.upper()
        lines = textwrap.wrap(text, width=18)
        if not lines:
            return pil_img

        from config import FONTS_DIR
        try:
            font_path_abs = FONTS_DIR / "arialbd.ttf"
            if font_path_abs.exists():
                font = ImageFont.truetype(str(font_path_abs), 55)
            elif os.name == 'nt' and os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 55)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(pil_img)

        # Đo toàn bộ block text
        line_bboxes = []
        for ln in lines:
            bb = draw.textbbox((0, 0), ln, font=font)
            line_bboxes.append((bb[2] - bb[0], bb[3] - bb[1]))

        line_h = line_bboxes[0][1] if line_bboxes else 80
        line_gap = 12
        total_text_h = len(lines) * line_h + (len(lines) - 1) * line_gap
        max_text_w = max(w for w, _ in line_bboxes)

        # Vị trí: giữa theo chiều ngang, 75% theo chiều dọc
        pad_x, pad_y = 40, 24
        box_x = (W - max_text_w) // 2 - pad_x
        box_y = int(H * 0.74) - pad_y
        box_w = max_text_w + pad_x * 2
        box_h = total_text_h + pad_y * 2

        # Vẽ background pill box (semi-transparent đen)
        overlay = PILImage.new("RGBA", pil_img.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        r = 24  # border radius
        ov_draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            radius=r,
            fill=(0, 0, 0, 175)
        )
        pil_img = PILImage.alpha_composite(pil_img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(pil_img)

        # Vẽ từng dòng text
        y_cursor = box_y + pad_y
        for ln, (lw, lh) in zip(lines, line_bboxes):
            x = (W - lw) // 2

            # Stroke đen
            sw = 4
            for dx in range(-sw, sw + 1):
                for dy in range(-sw, sw + 1):
                    if dx * dx + dy * dy <= sw * sw:
                        draw.text((x + dx, y_cursor + dy), ln, font=font, fill=(0, 0, 0))

            # Chữ trắng chính
            draw.text((x, y_cursor), ln, font=font, fill=(255, 255, 255))
            y_cursor += lh + line_gap

        return pil_img

    def make_frame(t):
        idx = min(int(t / img_dur), len(scaled_imgs) - 1)
        arr = scaled_imgs[idx]
        dir_val = directions[idx]

        # Ken Burns effect logic
        progress = (t % img_dur) / img_dur
        if dir_val == "out": progress = 1.0 - progress
        
        zoom = 1.0 + 0.15 * progress # Zoom 15%
        
        full_h, full_w = arr.shape[:2]
        crop_w = int(full_w / zoom)
        crop_h = int(full_h / zoom)
        
        # Center crop
        left = (full_w - crop_w) // 2
        top  = (full_h - crop_h) // 2
        
        crop = arr[top:top+crop_h, left:left+crop_w]
        pil  = Image.fromarray(crop).resize((W, H), Image.LANCZOS)
        
        # Subtitle — trả về pil đã được vẽ subtitle
        if subs:
            for start, end, text in subs:
                if start <= t <= end:
                    pil = _add_phrase_subtitle(pil, text, W, H)
                    break
                    
        return np.array(pil)

    clip = VideoClip(make_frame, duration=total_dur).with_fps(fps)
    try:
        clip = clip.with_audio(final_audio)
    except AttributeError:
        clip = clip.set_audio(final_audio)

    # Xuất file libx264 chất lượng cao
    clip.write_videofile(
        str(output_path),
        codec         = "libx264",
        audio_codec   = "aac",
        bitrate       = "6000k",
        preset        = "medium",
        logger        = None
    )

    clip.close()
    audio_clip.close()
    return str(output_path)

