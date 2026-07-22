"""Generate portrait images with Cloudflare Workers AI."""

from __future__ import annotations

import base64
import binascii
import logging
import secrets
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, UnidentifiedImageError

from config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_IMAGE_MODEL,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_REQUEST_TIMEOUT_SECONDS = 180
_MIN_IMAGE_DIMENSION = 256
_MAX_IMAGE_DIMENSION = 1920
_MAX_PROMPT_LENGTH = 2048
_FACELESS_RULE = (
    "CRITICAL COMPOSITION RULE: every human figure is faceless and unidentifiable, shown only "
    "from behind at long distance, as a tiny silhouette, with the head cropped out, or with the "
    "entire head hidden in deep shadow, glowing haze, cloth, or light; featureless shadow-shape "
    "heads with no eyes, no nose, no mouth, no skin detail, no facial contours, no front-facing "
    "person, no portrait, no headshot, no close-up, no three-quarter facial view"
)
_STYLE_SUFFIX = (
    "semi-abstract figurative oil painting on rough textured canvas, loose expressive "
    "impasto brushwork, indistinct simplified forms, soft blurred edges, atmospheric haze, "
    "dreamlike symbolic allegory, antique gold amber burnt orange ochre sienna and umber "
    "sunset palette, deep brown shadows, dramatic chiaroscuro, quiet negative space, painterly "
    "rather than literal, no photorealism, no anime, "
    "no crisp digital art, no glossy 3D, no neon colors, no blue-dominant lighting, no "
    "readable text, no watermark"
)


class ImageGenerationError(RuntimeError):
    """Raised when Cloudflare cannot produce a valid image."""


def _validate_configuration() -> None:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise ImageGenerationError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required for image generation"
        )


def _validate_dimensions(width: int, height: int) -> None:
    if not _MIN_IMAGE_DIMENSION <= width <= _MAX_IMAGE_DIMENSION:
        raise ValueError(
            f"Image width must be between {_MIN_IMAGE_DIMENSION} and {_MAX_IMAGE_DIMENSION}: {width}"
        )
    if not _MIN_IMAGE_DIMENSION <= height <= _MAX_IMAGE_DIMENSION:
        raise ValueError(
            f"Image height must be between {_MIN_IMAGE_DIMENSION} and {_MAX_IMAGE_DIMENSION}: {height}"
        )


def _extract_image_bytes(payload: dict[str, Any]) -> bytes:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ImageGenerationError(f"Cloudflare response is missing result: {payload}")
    image_value = result.get("image")
    if not isinstance(image_value, str) or not image_value:
        raise ImageGenerationError(f"Cloudflare response is missing result.image: {payload}")
    try:
        return base64.b64decode(image_value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ImageGenerationError("Cloudflare returned invalid base64 image data") from error


def _save_as_jpeg(image_bytes: bytes, output_path: Path) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            normalized = image.convert("RGB")
            normalized.save(output_path, format="JPEG", quality=94, optimize=True)
    except (UnidentifiedImageError, OSError) as error:
        raise ImageGenerationError("Cloudflare returned data that is not a valid image") from error
    if output_path.stat().st_size < 10_000:
        raise ImageGenerationError(
            f"Generated image is unexpectedly small: {output_path.stat().st_size} bytes"
        )


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                pass
    return min(2.0**attempt, 15.0)


def generate_single_image(
    prompt: str,
    output_path: str | Path,
    width: int = 768,
    height: int = 1344,
) -> bool:
    """Generate one image and save it as a validated JPEG."""
    _validate_configuration()
    _validate_dimensions(width, height)
    if not prompt.strip():
        raise ValueError("Image prompt cannot be empty")
    full_prompt = f"{_FACELESS_RULE}. SCENE: {prompt.strip()}. STYLE: {_STYLE_SUFFIX}"
    if len(full_prompt) > _MAX_PROMPT_LENGTH:
        raise ValueError(
            f"Image prompt exceeds Cloudflare's {_MAX_PROMPT_LENGTH}-character limit"
        )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}"
        f"/ai/run/{CLOUDFLARE_IMAGE_MODEL}"
    )
    multipart_fields = {
        "prompt": (None, full_prompt),
        "width": (None, str(width)),
        "height": (None, str(height)),
        "seed": (None, str(secrets.randbelow(2_147_483_647) + 1)),
    }
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}

    last_error: Exception | None = None
    max_retries = 4
    for attempt in range(max_retries):
        response: requests.Response | None = None
        try:
            response = requests.post(
                url,
                headers=headers,
                files=multipart_fields,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ImageGenerationError("Cloudflare returned a non-object JSON response")
                image_bytes = _extract_image_bytes(payload)
                _save_as_jpeg(image_bytes, destination)
                logger.info("Generated image %s (%s bytes)", destination.name, destination.stat().st_size)
                return True

            body = response.text[:500].replace("\n", " ")
            error = ImageGenerationError(
                f"Cloudflare image API returned HTTP {response.status_code}: {body}"
            )
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise error
            last_error = error
            logger.warning(
                "Cloudflare image retry %s/%s after HTTP %s",
                attempt + 1,
                max_retries,
                response.status_code,
            )
        except requests.RequestException as error:
            last_error = error
            logger.warning(
                "Cloudflare image network retry %s/%s: %s",
                attempt + 1,
                max_retries,
                error,
            )
        except (ValueError, ImageGenerationError) as error:
            last_error = error
            if response is None or response.status_code not in _RETRYABLE_STATUS_CODES:
                raise
        if attempt < max_retries - 1:
            time.sleep(_retry_delay(response, attempt))

    raise ImageGenerationError(
        f"Cloudflare image generation failed after {max_retries} attempts: {last_error}"
    ) from last_error


def generate_shorts_images(
    scenes: list[dict[str, Any]],
    output_dir: str | Path,
    video_id: str = "",
) -> list[str]:
    """Generate one 768x1344 image for every Shorts scene."""
    if not scenes:
        raise ValueError("At least one scene is required for image generation")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    generated_paths: list[str] = []

    for index, scene in enumerate(scenes):
        prompt_value = scene.get("visual_prompt") or scene.get("text")
        if not isinstance(prompt_value, str) or not prompt_value.strip():
            raise ValueError(f"Scene {index + 1} has no usable visual prompt")

        filename = (
            f"{video_id}_scene_{index + 1:02d}.jpg"
            if video_id
            else f"scene_{index + 1:02d}.jpg"
        )
        output_path = destination / filename
        if output_path.exists() and output_path.stat().st_size > 10_000:
            logger.info("Scene %s already exists; reusing %s", index + 1, output_path.name)
            generated_paths.append(str(output_path))
            continue

        logger.info("Generating scene %s/%s with %s", index + 1, len(scenes), CLOUDFLARE_IMAGE_MODEL)
        generate_single_image(prompt_value, output_path, width=768, height=1344)
        generated_paths.append(str(output_path))
        if index < len(scenes) - 1:
            time.sleep(2)

    return generated_paths
