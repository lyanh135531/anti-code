"""Memory-bounded 16:9 renderer for the independent long-form flow."""

from __future__ import annotations

import logging
import math
import os
import textwrap
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from modules.subtitle_parser import parse_srt_to_phrases

logger = logging.getLogger(__name__)


def _font(size: int, bold: bool = False):
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _prepare(path: str, width: int, height: int) -> np.ndarray:
    with Image.open(path) as source:
        image = source.convert("RGB")
        scale = max(width / image.width, height / image.height) * 1.16
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.LANCZOS)
        return np.asarray(image, dtype=np.uint8)


def _motion_frame(arr: np.ndarray, t_local: float, width: int, height: int) -> np.ndarray:
    # A subtle reframe every 5.5 seconds creates visual beats without synthetic video.
    beat = 5.5
    beat_index = int(t_local / beat)
    progress = (t_local % beat) / beat
    eased = 0.5 - 0.5 * math.cos(math.pi * progress)
    zoom = 1.035 + 0.045 * eased
    crop_w = min(arr.shape[1], int(width / zoom))
    crop_h = min(arr.shape[0], int(height / zoom))
    room_x = max(0, arr.shape[1] - crop_w)
    room_y = max(0, arr.shape[0] - crop_h)
    start_x, end_x = ((0.32, 0.68) if beat_index % 2 == 0 else (0.68, 0.32))
    start_y, end_y = ((0.42, 0.58) if beat_index % 3 else (0.55, 0.42))
    x = int(room_x * (start_x + (end_x - start_x) * eased))
    y = int(room_y * (start_y + (end_y - start_y) * eased))
    crop = arr[y : y + crop_h, x : x + crop_w]
    return np.asarray(Image.fromarray(crop).resize((width, height), Image.Resampling.BILINEAR))


def _caption_cues(srt_path: str | Path | None, line_width: int = 42) -> list[tuple[float, float, str]]:
    """Split phrase-level SRT into readable cues of no more than two lines."""
    if not srt_path:
        return []
    cues: list[tuple[float, float, str]] = []
    for phrase in parse_srt_to_phrases(str(srt_path)):
        current = []
        for word in phrase.words:
            candidate = " ".join(item.word for item in [*current, word])
            if current and len(textwrap.wrap(candidate, width=line_width)) > 2:
                text = "\n".join(textwrap.wrap(" ".join(item.word for item in current), width=line_width))
                cues.append((current[0].start, current[-1].end, text))
                current = [word]
            else:
                current.append(word)
        if current:
            text = "\n".join(textwrap.wrap(" ".join(item.word for item in current), width=line_width))
            cues.append((current[0].start, current[-1].end, text))
    return cues


def _decorate(
    frame: np.ndarray,
    overlay: str,
    channel_name: str,
    subtitle: str = "",
) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    draw.text(
        (width - 35, height - 32),
        channel_name,
        font=_font(22, bold=True),
        fill=(255, 255, 255, 155),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 130),
        anchor="rs",
    )
    if overlay:
        text = textwrap.fill(overlay, width=24)
        font = _font(52, bold=True)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=8, align="center")
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = width // 2, int(height * (0.72 if subtitle else 0.80))
        pad_x, pad_y = 34, 20
        draw.rounded_rectangle(
            (x - text_w // 2 - pad_x, y - text_h // 2 - pad_y,
             x + text_w // 2 + pad_x, y + text_h // 2 + pad_y),
            radius=18,
            fill=(0, 0, 0, 145),
        )
        draw.multiline_text(
            (x, y), text, font=font, fill=(255, 244, 214, 255), spacing=8,
            align="center", anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 210)
        )
    if subtitle:
        font = _font(42, bold=True)
        bbox = draw.multiline_textbbox(
            (0, 0), subtitle, font=font, spacing=8, align="center", stroke_width=2
        )
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = width // 2, int(height * 0.86)
        pad_x, pad_y = 24, 14
        draw.rounded_rectangle(
            (
                x - text_w // 2 - pad_x,
                y - text_h // 2 - pad_y,
                x + text_w // 2 + pad_x,
                y + text_h // 2 + pad_y,
            ),
            radius=12,
            fill=(0, 0, 0, 165),
        )
        draw.multiline_text(
            (x, y), subtitle, font=font, fill=(255, 255, 255, 255), spacing=8,
            align="center", anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 230),
        )
    return np.asarray(image)


def build_long_video(
    image_paths: list[str],
    overlays: list[str],
    audio_path: str,
    output_path: str | Path,
    channel_name: str,
    subtitle_path: str | Path | None = None,
    music_path: str | None = None,
    music_volume: float = 0.10,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> str:
    try:
        from moviepy import AudioFileClip, CompositeAudioClip, VideoClip, afx, vfx
    except ImportError as error:
        raise ImportError("Install moviepy to render long-form video") from error
    if not image_paths:
        raise ValueError("At least one image is required")
    if len(overlays) != len(image_paths):
        raise ValueError("overlays must match image_paths")
    for path in image_paths:
        if not Path(path).exists():
            raise FileNotFoundError(path)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration
    slot = duration / len(image_paths)
    crossfade = min(0.65, slot / 8)
    caption_cues = _caption_cues(subtitle_path)
    caption_starts = [cue[0] for cue in caption_cues]

    def active_subtitle(t: float) -> str:
        index = bisect_right(caption_starts, t) - 1
        if index >= 0 and t <= caption_cues[index][1]:
            return caption_cues[index][2]
        return ""

    @lru_cache(maxsize=4)
    def load(index: int) -> np.ndarray:
        return _prepare(image_paths[index], width, height)

    def make_frame(t: float) -> np.ndarray:
        index = min(int(t / slot), len(image_paths) - 1)
        local = t - index * slot
        frame = _motion_frame(load(index), local, width, height)
        if index + 1 < len(image_paths) and local >= slot - crossfade:
            alpha = (local - (slot - crossfade)) / crossfade
            next_frame = _motion_frame(load(index + 1), max(0, local - slot), width, height)
            frame = ((1 - alpha) * frame.astype(np.float32) + alpha * next_frame).astype(np.uint8)
        overlay = overlays[index] if 0.35 <= local <= min(slot - 0.35, 4.8) else ""
        return _decorate(frame, overlay, channel_name, active_subtitle(t))

    video = VideoClip(make_frame, duration=duration).with_fps(fps)
    final_audio = audio
    music = None
    if music_path and Path(music_path).exists():
        music = AudioFileClip(str(music_path)).with_volume_scaled(music_volume)
        if music.duration < duration:
            music = music.with_effects([afx.AudioLoop(duration=duration)])
        music = music.subclipped(0, duration)
        final_audio = CompositeAudioClip([audio, music])
    video = video.with_audio(final_audio).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(1.2)])
    try:
        video.write_videofile(
            str(output), codec="libx264", audio_codec="aac", fps=fps,
            bitrate="5000k", audio_bitrate="192k", preset="fast",
            ffmpeg_params=["-movflags", "+faststart"], logger=None,
        )
    finally:
        video.close()
        if final_audio is not audio:
            final_audio.close()
        if music is not None:
            music.close()
        audio.close()
        load.cache_clear()
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Long-form renderer produced no output")
    logger.info("Long-form video complete: %s", output)
    return str(output)
