"""Landscape image generation with a resumable prompt/seed manifest."""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

from config import LONG_MAX_IMAGES, LONG_MIN_IMAGES
from modules.cloudflare_image_gen import generate_single_image
from modules.thumbnail_maker import create_thumbnail


CHARACTER_BIBLE = (
    "Recurring holy teacher: ivory robe, muted crimson mantle, dark shoulder-length hair, "
    "face shown only in profile, distance, or shadow. Recurring disciples: earth-tone linen "
    "robes with stable individual accent colors. Historically restrained first-century Judea. "
    "Landscape 16:9 composition with generous safe margins for slow camera movement"
)


def generate_long_images(
    prompts: list[str], output_dir: str | Path, video_id: str
) -> tuple[list[str], str]:
    if not LONG_MIN_IMAGES <= len(prompts) <= LONG_MAX_IMAGES:
        raise ValueError(
            f"Long-form requires {LONG_MIN_IMAGES}-{LONG_MAX_IMAGES} prompts, got {len(prompts)}"
        )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "image_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"video_id": video_id, "width": 1344, "height": 768, "images": []}

    by_index = {item["index"]: item for item in manifest.get("images", [])}
    paths: list[str] = []
    for index, prompt in enumerate(prompts, 1):
        filename = f"{video_id}_visual_{index:02d}.jpg"
        path = destination / filename
        prior = by_index.get(index)
        seed = int(prior["seed"]) if prior else secrets.randbelow(2_147_483_647) + 1
        full_prompt = f"{CHARACTER_BIBLE}. Scene: {prompt}"
        if path.exists() and path.stat().st_size > 10_000:
            paths.append(str(path))
            continue
        generate_single_image(full_prompt, path, width=1344, height=768, seed=seed)
        by_index[index] = {
            "index": index,
            "file": filename,
            "seed": seed,
            "prompt": full_prompt,
        }
        manifest["images"] = [by_index[key] for key in sorted(by_index)]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(str(path))
        if index < len(prompts):
            time.sleep(1.5)
    return paths, str(manifest_path)


def generate_long_thumbnail(
    prompt: str,
    thumbnail_text: str,
    output_dir: str | Path,
    video_id: str,
) -> str:
    if not 2 <= len(thumbnail_text.split()) <= 4:
        raise ValueError("Long-form thumbnail text must contain 2-4 words")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    raw_path = destination / f"{video_id}_thumbnail_raw.jpg"
    final_path = destination / f"{video_id}_thumbnail.jpg"
    seed_path = destination / f"{video_id}_thumbnail.json"
    if final_path.exists() and final_path.stat().st_size > 10_000:
        return str(final_path)
    seed = secrets.randbelow(2_147_483_647) + 1
    hero_prompt = (
        f"{CHARACTER_BIBLE}. YouTube thumbnail hero composition, one clear subject, strong "
        f"light-dark contrast, no written text, no symbols floating in space. Scene: {prompt}"
    )
    generate_single_image(hero_prompt, raw_path, width=1344, height=768, seed=seed)
    seed_path.write_text(
        json.dumps({"seed": seed, "prompt": hero_prompt}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return create_thumbnail(
        image_path=str(raw_path),
        title=thumbnail_text,
        religion="Christianity",
        output_path=final_path,
    )
