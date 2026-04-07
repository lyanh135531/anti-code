"""
==========================================================
  MODULE: VIDEO MAKER
  Dựng video 1920x1080 từ ảnh + audio bằng MoviePy + Pillow
  Hiệu ứng: Ken Burns (zoom/pan), crossfade, watermark
==========================================================
"""

import logging
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


# ============================================================
# XỬ LÝ ẢNH: KEN BURNS EFFECT
# ============================================================

def _make_ken_burns_frames(
    img_path: str,
    duration: float,
    W: int = 1920,
    H: int = 1080,
    fps: int = 24,
    direction: str = "in"
) -> np.ndarray:
    """
    Tạo các frame cho hiệu ứng Ken Burns (zoom + pan).
    direction: "in" (zoom vào) hoặc "out" (zoom ra)
    
    Returns:
        numpy array shape (n_frames, H, W, 3)
    """
    img = Image.open(img_path).convert("RGB")

    # Scale ảnh để lớn hơn target (cần zoom)
    scale = max(W / img.width, H / img.height) * 1.18
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)
    arr   = np.array(img, dtype=np.uint8)

    n_frames = int(duration * fps)
    frames   = []

    for i in range(n_frames):
        t        = i / max(n_frames - 1, 1)  # 0.0 → 1.0
        progress = t if direction == "in" else (1.0 - t)

        zoom = 1.0 + 0.12 * progress  # Zoom 0% → 12%

        # Kích thước crop (chia zoom hệ số)
        crop_w = int(W / zoom)
        crop_h = int(H / zoom)

        # Pan ngang nhẹ
        pan_x = int((new_w - crop_w) * 0.5 + (new_w - crop_w) * 0.1 * progress)
        pan_y = int((new_h - crop_h) * 0.5)

        # Clamp
        pan_x = max(0, min(pan_x, new_w - crop_w))
        pan_y = max(0, min(pan_y, new_h - crop_h))

        crop = arr[pan_y:pan_y + crop_h, pan_x:pan_x + crop_w]

        # Resize về W×H bằng PIL (nhanh hơn scipy)
        pil_crop = Image.fromarray(crop).resize((W, H), Image.BILINEAR)
        frames.append(np.array(pil_crop, dtype=np.uint8))

    return np.stack(frames, axis=0)


# ============================================================
# CROSSFADE GIỮA 2 CLIP
# ============================================================

def _crossfade(frames_a: np.ndarray, frames_b: np.ndarray, n_fade: int) -> np.ndarray:
    """
    Ghép 2 mảng frames với hiệu ứng crossfade.
    frames_a: (Na, H, W, 3)
    frames_b: (Nb, H, W, 3)
    n_fade:   Số frame crossfade
    """
    n_fade = min(n_fade, len(frames_a), len(frames_b))
    
    main_a   = frames_a[:-n_fade]  # Phần chính của clip A
    fade_a   = frames_a[-n_fade:]  # Phần cuối A (fade out)
    fade_b   = frames_b[:n_fade]   # Phần đầu B (fade in)
    main_b   = frames_b[n_fade:]   # Phần chính của clip B

    blended = []
    for i in range(n_fade):
        alpha = i / n_fade
        mix   = ((1 - alpha) * fade_a[i].astype(float) +
                  alpha       * fade_b[i].astype(float)).astype(np.uint8)
        blended.append(mix)

    return np.concatenate([main_a, np.stack(blended), main_b], axis=0)


# ============================================================
# THÊM WATERMARK / BRANDING
# ============================================================

def _add_watermark_to_frame(frame: np.ndarray, channel_name: str) -> np.ndarray:
    """Thêm watermark kênh góc dưới phải."""
    pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil)

    W, H = pil.size
    text = f"◆ {channel_name}"

    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    # Vẽ shadow
    draw.text((W - 305, H - 52), text, font=font, fill=(0, 0, 0, 160))
    # Vẽ chữ trắng
    draw.text((W - 307, H - 54), text, font=font, fill=(255, 255, 255, 200))

    return np.array(pil)


# ============================================================
# BUILD VIDEO CHÍNH
# ============================================================

def build_video(
    image_paths:   list[str],
    audio_path:    str,
    output_path:   str | Path,
    channel_name:  str  = "Sacred Wisdom Daily",
    music_path:    str  = None,
    music_volume:  float = 0.10,
    img_duration:  float = 6.0,
    fade_duration: float = 0.8,
    W: int = 1920,
    H: int = 1080,
    fps: int = 24,
) -> str:
    """
    Tạo video MP4 từ ảnh + audio.

    Args:
        image_paths:   Danh sách đường dẫn ảnh
        audio_path:    File audio MP3/FLAC
        output_path:   Đường dẫn output video
        channel_name:  Tên kênh cho watermark
        music_path:    Nhạc nền tùy chọn (None = không dùng)
        music_volume:  Âm lượng nhạc nền (0.0-1.0)
        img_duration:  Giây mỗi ảnh
        fade_duration: Giây crossfade
        
    Returns:
        Đường dẫn video đã tạo
    """
    try:
        from moviepy.editor import (
            AudioFileClip, VideoClip, CompositeAudioClip,
            AudioFileClip as AFC
        )
    except ImportError:
        raise ImportError("Hãy cài: pip install moviepy")

    output_path = Path(output_path)
    logger.info(f"Bắt đầu dựng video: {len(image_paths)} ảnh → {output_path.name}")

    # ── 1. Đọc audio duration ──────────────────────────────
    audio_clip   = AudioFileClip(str(audio_path))
    total_audio  = audio_clip.duration
    logger.info(f"Audio duration: {total_audio:.1f}s")

    # ── 2. Tính số frame mỗi ảnh ───────────────────────────
    n_imgs    = len(image_paths)
    n_fade    = int(fade_duration * fps)
    # Điều chỉnh img_duration để tổng khớp audio
    total_duration = total_audio + 2.0  # 2s buffer ở cuối
    img_dur   = max(3.0, total_duration / n_imgs)

    directions = ["in", "out"] * (n_imgs // 2 + 1)  # Xen kẽ zoom in/out

    # ── 3. Tạo frames cho tất cả ảnh ───────────────────────
    all_frames = None
    for i, img_path in enumerate(image_paths):
        logger.info(f"  Render ảnh {i+1}/{n_imgs}: {Path(img_path).name}")
        try:
            frames = _make_ken_burns_frames(
                img_path, img_dur, W, H, fps, direction=directions[i]
            )
        except Exception as e:
            logger.warning(f"  Lỗi ảnh {img_path}: {e} — bỏ qua")
            continue

        if all_frames is None:
            all_frames = frames
        else:
            all_frames = _crossfade(all_frames, frames, n_fade)

    if all_frames is None:
        raise RuntimeError("Không có frame nào được tạo!")

    total_frames = len(all_frames)
    video_dur    = total_frames / fps
    logger.info(f"Tổng: {total_frames} frames = {video_dur:.1f}s")

    # ── 4. Thêm watermark vào 1 vài frame (không phải tất cả để nhanh hơn) ──
    # Thêm watermark vào frame cuối mỗi segment
    watermark_interval = fps * 10   # Mỗi 10 giây 1 watermark
    for fi in range(0, total_frames, watermark_interval):
        all_frames[fi] = _add_watermark_to_frame(all_frames[fi], channel_name)

    # ── 5. Tạo VideoClip từ frames ─────────────────────────
    def make_frame(t):
        fi = min(int(t * fps), total_frames - 1)
        return all_frames[fi]

    video_clip = VideoClip(make_frame, duration=video_dur)
    video_clip = video_clip.set_fps(fps)

    # ── 6. Ghép audio ──────────────────────────────────────
    # Trim audio nếu video ngắn hơn audio
    if total_audio > video_dur:
        audio_clip = audio_clip.subclip(0, video_dur)
    
    if music_path and os.path.exists(music_path):
        try:
            music_clip = AudioFileClip(str(music_path)).volumex(music_volume)
            # Loop nhạc nếu cần
            if music_clip.duration < video_dur:
                loops = int(video_dur / music_clip.duration) + 1
                from moviepy.audio.fx.all import audio_loop
                music_clip = audio_loop(music_clip, nloops=loops).subclip(0, video_dur)
            else:
                music_clip = music_clip.subclip(0, video_dur)
            final_audio = CompositeAudioClip([audio_clip, music_clip])
            logger.info(f"Đã thêm nhạc nền: {Path(music_path).name}")
        except Exception as e:
            logger.warning(f"Không thể thêm nhạc nền: {e}")
            final_audio = audio_clip
    else:
        final_audio = audio_clip

    video_clip = video_clip.set_audio(final_audio)

    # ── 7. Fade in / Fade out ──────────────────────────────
    from moviepy.video.fx.all import fadein, fadeout
    video_clip = fadein(video_clip, duration=1.0)
    video_clip = fadeout(video_clip, duration=1.5)

    # ── 8. Export ──────────────────────────────────────────
    logger.info(f"Đang export video (có thể mất vài phút)...")
    video_clip.write_videofile(
        str(output_path),
        codec       = "libx264",
        audio_codec = "aac",
        bitrate     = "3000k",
        audio_bitrate = "192k",
        preset      = "fast",        # "fast" vs "slow" — cân bằng tốc độ/chất lượng
        ffmpeg_params = ["-movflags", "+faststart"],  # Cho phép stream nhanh
        logger      = None,          # Tắt progress bar verbose
        verbose     = False,
    )

    # Cleanup
    audio_clip.close()
    video_clip.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✅ Video hoàn thành: {output_path} ({size_mb:.1f} MB)")
    return str(output_path)
