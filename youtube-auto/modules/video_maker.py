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
# XỬ LÝ ẢNH: KEN BURNS EFFECT (LAZY LOADING - TIẾT KIỆM RAM)
# ============================================================

def load_scaled_image(img_path: str, W: int = 1920, H: int = 1080) -> np.ndarray:
    """Tải và scale ảnh sẵn 1 lần, lưu vào RAM thay vì lưu toàn bộ frame."""
    img = Image.open(img_path).convert("RGB")
    scale = max(W / img.width, H / img.height) * 1.18
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    return np.array(img, dtype=np.uint8)


def get_ken_burns_frame(
    arr: np.ndarray, 
    t_local: float, 
    duration: float, 
    W: int = 1920, 
    H: int = 1080, 
    direction: str = "in"
) -> np.ndarray:
    """Tính toán on-the-fly 1 frame cho hiệu ứng Ken Burns tại thời gian t_local."""
    progress = t_local / max(duration, 0.001)
    progress = max(0.0, min(1.0, progress))
    if direction == "out":
        progress = 1.0 - progress

    zoom = 1.0 + 0.12 * progress
    crop_w = int(W / zoom)
    crop_h = int(H / zoom)

    new_h, new_w = arr.shape[:2]
    
    pan_x = int((new_w - crop_w) * 0.5 + (new_w - crop_w) * 0.1 * progress)
    pan_y = int((new_h - crop_h) * 0.5)

    pan_x = max(0, min(pan_x, new_w - crop_w))
    pan_y = max(0, min(pan_y, new_h - crop_h))

    crop = arr[pan_y:pan_y + crop_h, pan_x:pan_x + crop_w]
    pil_crop = Image.fromarray(crop).resize((W, H), Image.BILINEAR)
    return np.array(pil_crop, dtype=np.uint8)


# ============================================================
# THÊM WATERMARK / BRANDING
# ============================================================

def _add_watermark_to_frame(frame: np.ndarray, channel_name: str) -> np.ndarray:
    """Thêm watermark kênh góc dưới phải."""
    pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil)

    W, H = pil.size
    text = f"◆ {channel_name}"

    try:
        font = ImageFont.truetype("arial.ttf", 28) if os.name == 'nt' else ImageFont.load_default()
    except OSError:
        font = ImageFont.load_default()

    draw.text((W - 305, H - 52), text, font=font, fill=(0, 0, 0, 160))
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
    Tạo video MP4 từ ảnh + audio (sử dụng lazy frame evaluation ránh tràn RAM).

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
        from moviepy import (
            AudioFileClip, VideoClip, CompositeAudioClip, vfx, afx
        )
    except ImportError:
        raise ImportError("Hãy cài: pip install moviepy")

    output_path = Path(output_path)
    logger.info(f"Bắt đầu dựng video: {len(image_paths)} ảnh → {output_path.name}")

    # ── 1. Đọc audio duration ──────────────────────────────
    audio_clip   = AudioFileClip(str(audio_path))
    total_audio  = audio_clip.duration
    logger.info(f"Audio duration: {total_audio:.1f}s")

    # ── 2. Tải và chuẩn bị mảng ảnh (tránh lỗi RAM) ────────
    scaled_images = []
    valid_paths = []
    for img_path in image_paths:
        try:
            arr = load_scaled_image(img_path, W, H)
            scaled_images.append(arr)
            valid_paths.append(img_path)
        except Exception as e:
            logger.warning(f"Lỗi đọc ảnh {img_path}: {e} — bỏ qua")

    n_imgs = len(scaled_images)
    if n_imgs == 0:
        raise RuntimeError("Không có ảnh nào đọc được!")

    # ── 3. Tính toán thời lượng khớp audio ─────────────────
    target_dur = total_audio + 2.0  # 2s buffer ở cuối
    
    # n_imgs = số ảnh. Công thức tổng duration = img_dur + (n_imgs - 1)*(img_dur - fade_duration)
    # => target_dur = img_dur * n_imgs - fade_duration * (n_imgs - 1)
    img_dur = (target_dur + fade_duration * (n_imgs - 1)) / n_imgs
    img_dur = max(3.0, img_dur)
    
    step_time = img_dur - fade_duration
    video_dur = img_dur + (n_imgs - 1) * step_time

    directions = ["in", "out"] * (n_imgs // 2 + 1)
    logger.info(f"Dựng {n_imgs} ảnh, img_dur: {img_dur:.1f}s, tổng video: {video_dur:.1f}s")

    # ── 4. Hàm generate khung hình động (lazy evaluation) ──
    def make_frame(t):
        idx = int(t / step_time)
        if idx >= n_imgs:
            idx = n_imgs - 1
            
        t_local_1 = t - idx * step_time
        frame1 = get_ken_burns_frame(scaled_images[idx], t_local_1, img_dur, W, H, directions[idx])
        
        # Crossfade nếu trong vùng chuyển tiếp
        if t_local_1 > step_time and idx + 1 < n_imgs:
            alpha = (t_local_1 - step_time) / fade_duration
            alpha = max(0.0, min(1.0, alpha))
            
            t_local_2 = t - (idx + 1) * step_time
            frame2 = get_ken_burns_frame(scaled_images[idx + 1], t_local_2, img_dur, W, H, directions[idx + 1])
            frame1 = ((1.0 - alpha) * frame1.astype(float) + alpha * frame2.astype(float)).astype(np.uint8)
        
        # Chỉ chèn watermark sau mỗi 10 giây một frame (như code cũ) hoặc luôn luôn.
        # Ở đây ta chèn watermark luôn 1 chỗ cố định để đẹp.
        return _add_watermark_to_frame(frame1, channel_name)

    video_clip = VideoClip(make_frame, duration=video_dur)
    video_clip = video_clip.with_fps(fps)

    # ── 5. Ghép audio ──────────────────────────────────────
    if total_audio > video_dur:
        audio_clip = audio_clip.subclipped(0, video_dur)
    
    if music_path and os.path.exists(music_path):
        try:
            music_clip = AudioFileClip(str(music_path)).with_volume_scaled(music_volume)
            if music_clip.duration < video_dur:
                music_clip = music_clip.with_effects([afx.AudioLoop(duration=video_dur)]).subclipped(0, video_dur)
            else:
                music_clip = music_clip.subclipped(0, video_dur)
            final_audio = CompositeAudioClip([audio_clip, music_clip])
            logger.info(f"Đã thêm nhạc nền.")
        except Exception as e:
            logger.warning(f"Không thể thêm nhạc nền: {e}")
            final_audio = audio_clip
    else:
        final_audio = audio_clip

    video_clip = video_clip.with_audio(final_audio)

    # ── 6. Fade in / Fade out ──────────────────────────────
    video_clip = video_clip.with_effects([vfx.FadeIn(1.0), vfx.FadeOut(1.5)])

    # ── 7. Export ──────────────────────────────────────────
    logger.info(f"Đang export video (có thể mất vài phút)...")
    video_clip.write_videofile(
        str(output_path),
        codec       = "libx264",
        audio_codec = "aac",
        bitrate     = "3000k",
        audio_bitrate = "192k",
        preset      = "fast",
        ffmpeg_params = ["-movflags", "+faststart"],
        logger      = None
    )

    audio_clip.close()
    video_clip.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✅ Video hoàn thành: {output_path.name} ({size_mb:.1f} MB)")
    return str(output_path)
