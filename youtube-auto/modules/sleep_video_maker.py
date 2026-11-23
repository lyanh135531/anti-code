"""Ultra-fast FFmpeg-based video and audio builder for 1-2 hour Sleep Bible videos."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from PIL import Image

logger = logging.getLogger(__name__)


def _run_cmd(cmd: list[str], description: str) -> None:
    logger.info("Executing: %s", " ".join(cmd[:12]) + ("..." if len(cmd) > 12 else ""))
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        logger.error("%s failed with code %d:\n%s", description, process.returncode, process.stderr[-1000:])
        raise RuntimeError(f"{description} failed: {process.stderr[-500:]}")


def _normalize_image_for_video(src_path: Path | str, dst_path: Path | str, width: int = 1920, height: int = 1080) -> None:
    """Ensure image is exactly width x height in RGB with subtle vignette and dark-mode tone."""
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        scale = max(width / img.width, height / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        cropped = resized.crop((left, top, left + width, top + height))
        cropped.save(dst_path, format="JPEG", quality=95)


def prepare_sleep_audio(
    voice_path: str | Path,
    music_path: str | Path | None,
    output_path: str | Path,
    target_duration_sec: int = 5400,
    music_volume: float = 0.22,
) -> str:
    """Mix voice with looped ambient/rain music padded to target_duration_sec."""
    voice_file = Path(voice_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not voice_file.exists():
        raise FileNotFoundError(f"Voice file not found: {voice_file}")

    fade_out_start = max(0, target_duration_sec - 15)

    if music_path and Path(music_path).exists():
        bg_file = Path(music_path)
        logger.info("Mixing voice with ambient background music: %s", bg_file.name)
        # Using apad on voice, aloop on background music, mixing and fading out at target_duration
        filter_complex = (
            f"[0:a]apad=whole_dur={target_duration_sec}[va];"
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{target_duration_sec},volume={music_volume}[bga];"
            f"[va][bga]amix=inputs=2:duration=first:dropout_transition=0,afade=t=out:st={fade_out_start}:d=15[outa]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(voice_file),
            "-i", str(bg_file),
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            str(output_file),
        ]
    else:
        logger.info("No background music file provided; generating gentle ambient rain pad with anoisesrc")
        filter_complex = (
            f"[0:a]apad=whole_dur={target_duration_sec}[va];"
            f"[1:a]volume=0.035,lowpass=f=1200,highpass=f=200[bga];"
            f"[va][bga]amix=inputs=2:duration=first:dropout_transition=0,afade=t=out:st={fade_out_start}:d=15[outa]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(voice_file),
            "-f", "lavfi",
            "-i", f"anoisesrc=d={target_duration_sec}:c=pink:r=44100:a=0.04",
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            str(output_file),
        ]

    _run_cmd(cmd, "Sleep audio mixing")
    return str(output_file)


def build_sleep_base_video(
    image_paths: Sequence[str | Path],
    output_path: str | Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    display_per_image: float = 35.0,
    crossfade: float = 3.0,
) -> str:
    """Build a seamless 2-3 minute looping base clip with smooth crossfades between images."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_file.parent / f"_temp_images_{output_file.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        valid_paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not valid_paths:
            raise ValueError("No valid image paths provided")

        # Prepare normalized 1080p images
        normalized_paths: list[Path] = []
        for i, src in enumerate(valid_paths):
            dst = temp_dir / f"norm_{i:02d}.jpg"
            _normalize_image_for_video(src, dst, width=width, height=height)
            normalized_paths.append(dst)

        # To ensure seamless loop across stream_loop repeats, append the first image at the end
        normalized_paths.append(normalized_paths[0])
        n = len(normalized_paths)

        # Build ffmpeg input arguments and xfade filter chain
        cmd: list[str] = ["ffmpeg", "-y"]
        for p in normalized_paths:
            cmd.extend(["-loop", "1", "-t", str(display_per_image), "-i", str(p)])

        filter_parts: list[str] = []
        current_layer = "0:v"
        
        for i in range(1, n):
            next_input = f"{i}:v"
            offset = i * (display_per_image - crossfade)
            out_layer = f"v{i}" if i < n - 1 else "vout"
            filter_parts.append(
                f"[{current_layer}][{next_input}]xfade=transition=fade:duration={crossfade}:offset={offset:.2f}[{out_layer}]"
            )
            current_layer = out_layer

        filter_str = ";".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_str,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "faster",
            "-crf", "22",
            "-r", str(fps),
            str(output_file),
        ])

        _run_cmd(cmd, "Sleep base video rendering")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return str(output_file)


def build_final_sleep_video(
    base_video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
) -> str:
    """Stream-copy muxing base video loop with audio for maximum speed on GitHub Actions."""
    base_video = Path(base_video_path)
    audio_file = Path(audio_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not base_video.exists():
        raise FileNotFoundError(f"Base video not found: {base_video}")
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(base_video),
        "-i", str(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_file),
    ]

    _run_cmd(cmd, "Final sleep video stream-copy muxing")
    return str(output_file)
