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

    # Xử lý Subtitles: Word-by-word timing
    subtitle_phrases = []
    if vtt_path and os.path.exists(vtt_path):
        from modules.subtitle_parser import parse_srt_to_phrases
        subtitle_phrases = parse_srt_to_phrases(str(vtt_path))
        logger.info(f"Đã nạp {len(subtitle_phrases)} phrases cho word-by-word subtitle.")

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

    def _add_word_highlight_subtitle(pil_img, subtitle_phrases, t, W, H):
        """
        Word-by-word highlight subtitle (Modern Highlighted Phrase Style).
        - Active word: large, yellow (#FFD700), centered in its slot with a thick outline
        - Inactive words: smaller, white, centered in their slots with a thin outline
        - All words laid out statically based on active word size (no layout shifts)
        - Position: upper-center (centered around ~45% height) inside a dark pill background
        """
        from modules.subtitle_parser import get_active_word
        from PIL import ImageFont, ImageDraw, Image as PILImage
        
        active = get_active_word(subtitle_phrases, t)
        if not active:
            return pil_img
        
        word_text, word_idx, phrase_idx = active
        phrase = subtitle_phrases[phrase_idx]
        all_words = [w.word.upper() for w in phrase.words]
        
        # Fonts
        from config import FONTS_DIR
        try:
            font_large_path = FONTS_DIR / "arialbd.ttf"
            if font_large_path.exists():
                font_base = ImageFont.truetype(str(font_large_path), 64)
                font_active = ImageFont.truetype(str(font_large_path), 78)
            elif os.name == 'nt' and os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                font_base = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 64)
                font_active = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 78)
            else:
                font_base = ImageFont.load_default()
                font_active = ImageFont.load_default()
        except Exception:
            font_base = ImageFont.load_default()
            font_active = ImageFont.load_default()
            
        img = pil_img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Để layout ổn định và không đè chữ, ta đo kích thước tất cả từ theo font_active (max size)
        space_w = draw.textlength(" ", font=font_active)
        word_gap = space_w + 10  # Khoảng cách giữa các từ
        
        # Đo kích thước từng từ theo cả 2 font
        word_sizes_base = []
        word_sizes_active = []
        for w in all_words:
            w_base = draw.textlength(w, font=font_base)
            w_act = draw.textlength(w, font=font_active)
            bb_base = draw.textbbox((0, 0), w, font=font_base)
            bb_act = draw.textbbox((0, 0), w, font=font_active)
            word_sizes_base.append((w_base, bb_base[3] - bb_base[1]))
            word_sizes_active.append((w_act, bb_act[3] - bb_act[1]))
            
        # Chia dòng tự động dựa trên kích thước active để luôn đủ chỗ vẽ
        max_line_width = W - 160  # Margin 80px mỗi bên
        lines = []
        current_line = []
        current_width = 0
        
        for idx, w in enumerate(all_words):
            ww_act, wh_act = word_sizes_active[idx]
            if current_line and current_width + word_gap + ww_act > max_line_width:
                lines.append(current_line)
                current_line = []
                current_width = 0
            
            if current_line:
                current_width += word_gap
            current_line.append((idx, w))
            current_width += ww_act
            
        if current_line:
            lines.append(current_line)
            
        # Tính toán tổng chiều cao và y_start
        line_spacing = 25
        total_height = 0
        line_heights = []
        for line in lines:
            lh = max(word_sizes_active[idx][1] for idx, _ in line)
            line_heights.append(lh)
            total_height += lh
        total_height += line_spacing * (len(lines) - 1)
        
        y_start = int(H * 0.45) - total_height // 2
        
        # Vẽ pill background đen mờ bao quanh toàn bộ text block
        max_line_w_actual = 0
        for line in lines:
            lw = sum(word_sizes_active[idx][0] for idx, _ in line) + word_gap * (len(line) - 1)
            if lw > max_line_w_actual:
                max_line_w_actual = lw
        
        pill_padding_x = 45
        pill_padding_y = 35
        pill_x1 = W // 2 - max_line_w_actual // 2 - pill_padding_x
        pill_y1 = y_start - pill_padding_y
        pill_x2 = W // 2 + max_line_w_actual // 2 + pill_padding_x
        pill_y2 = y_start + total_height + pill_padding_y
        
        overlay = PILImage.new("RGBA", img.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rounded_rectangle(
            [pill_x1, pill_y1, pill_x2, pill_y2],
            radius=25,
            fill=(0, 0, 0, 150) # Semi-transparent black pill
        )
        img = PILImage.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Vẽ từng từ
        y_cursor = y_start
        for line_idx, line in enumerate(lines):
            line_h = line_heights[line_idx]
            line_w = sum(word_sizes_active[idx][0] for idx, _ in line) + word_gap * (len(line) - 1)
            x_cursor = (W - line_w) // 2
            
            for idx, w_text in line:
                ww_base, wh_base = word_sizes_base[idx]
                ww_act, wh_act = word_sizes_active[idx]
                
                # Tâm của ô chứa từ này (tính theo kích thước active)
                cx = x_cursor + ww_act / 2
                cy = y_cursor + line_h / 2
                
                if idx == word_idx:
                    # Active word: vẽ căn giữa ô bằng font_active
                    draw_x = cx - ww_act / 2
                    draw_y = cy - wh_act / 2
                    
                    # Viền chữ đen dày cho chữ active
                    sw = 5
                    for dx in range(-sw, sw + 1):
                        for dy in range(-sw, sw + 1):
                            if dx * dx + dy * dy <= sw * sw:
                                draw.text((draw_x + dx, draw_y + dy), w_text, font=font_active, fill=(0, 0, 0))
                    
                    # Chữ chính màu vàng nổi bật
                    draw.text((draw_x, draw_y), w_text, font=font_active, fill=(255, 223, 0))
                else:
                    # Inactive word: vẽ căn giữa ô bằng font_base
                    draw_x = cx - ww_base / 2
                    draw_y = cy - wh_base / 2
                    
                    # Viền chữ đen mỏng hơn
                    sw = 3
                    for dx in range(-sw, sw + 1):
                        for dy in range(-sw, sw + 1):
                            if dx * dx + dy * dy <= sw * sw:
                                draw.text((draw_x + dx, draw_y + dy), w_text, font=font_base, fill=(0, 0, 0))
                                
                    # Chữ màu trắng
                    draw.text((draw_x, draw_y), w_text, font=font_base, fill=(255, 255, 255))
                
                # Tiến tới từ tiếp theo (theo kích thước ô active để giữ nguyên khoảng cách)
                x_cursor += ww_act + word_gap
            
            y_cursor += line_h + line_spacing
        
        return img.convert("RGB")

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
        
        # Subtitle — word-by-word highlight
        if subtitle_phrases:
            pil = _add_word_highlight_subtitle(pil, subtitle_phrases, t, W, H)
                    
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

