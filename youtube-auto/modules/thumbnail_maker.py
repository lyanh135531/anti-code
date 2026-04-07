"""
==========================================================
  MODULE: THUMBNAIL MAKER
  Tạo thumbnail đẹp 1280x720 bằng Pillow (không cần Canva)
  Tính năng: Gradient overlay, bold title, religion icon
==========================================================
"""

import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from config import (
    THUMB_WIDTH, THUMB_HEIGHT, RELIGION_COLORS,
    THUMB_FONT_SIZE_TITLE, THUMB_FONT_SIZE_SUBTITLE,
    THUMB_OVERLAY_ALPHA, CHANNEL_NAME
)

logger = logging.getLogger(__name__)


# ============================================================
# LOAD FONT (tự tìm font tốt nhất có sẵn)
# ============================================================

def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Tìm và load font tốt nhất có sẵn trên hệ thống."""
    # Danh sách font ưu tiên (Windows + Linux)
    bold_fonts = [
        "arialbd.ttf", "Arial Bold.ttf",
        "calibrib.ttf", "Calibri Bold.ttf",
        "trebucbd.ttf", "verdanab.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
    ]
    regular_fonts = [
        "arial.ttf", "Arial.ttf",
        "calibri.ttf", "Calibri.ttf",
        "verdana.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]

    candidates = bold_fonts if bold else regular_fonts

    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    # Fallback: font mặc định của PIL
    logger.warning("Không tìm thấy font TrueType, dùng PIL default font")
    return ImageFont.load_default()


# ============================================================
# GRADIENT OVERLAY
# ============================================================

def _add_gradient_overlay(img: Image.Image, color: tuple, alpha: int = 140) -> Image.Image:
    """
    Thêm gradient overlay màu đậm từ dưới lên để text dễ đọc.
    color: (R, G, B)
    alpha: 0-255 (độ mờ)
    """
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient: từ trong suốt (trên) đến tối đặc (dưới)
    for y in range(H):
        # Bắt đầu gradient từ 30% chiều cao
        ratio = max(0.0, (y - H * 0.25) / (H * 0.75))
        a = int(alpha * ratio)
        # Màu theo religion với gradient
        r = int(color[0] * 0.3 * ratio)
        g = int(color[1] * 0.3 * ratio)
        b = int(color[2] * 0.3 * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b, a))

    # Thêm vignette (tối 4 góc)
    for y in range(H):
        for side in ["left", "right"]:
            vignette_w = W // 5
            for x_offset in range(vignette_w):
                x = x_offset if side == "left" else W - 1 - x_offset
                ratio = (vignette_w - x_offset) / vignette_w * 0.5
                a = int(80 * ratio)
                draw.point((x, y), fill=(0, 0, 0, a))

    img_rgba = img.convert("RGBA")
    return Image.alpha_composite(img_rgba, overlay).convert("RGB")


# ============================================================
# DECORATIVE ELEMENTS
# ============================================================

def _add_decorative_bar(draw: ImageDraw.Draw, y: int, W: int, color: tuple):
    """Thêm đường kẻ trang trí màu."""
    draw.rectangle([(60, y), (W - 60, y + 4)], fill=color)


def _add_religion_symbol(draw: ImageDraw.Draw, religion: str, x: int, y: int, color: tuple):
    """Vẽ symbol unicode đơn giản cho religion."""
    symbols = {
        "Buddhism":    "☸",
        "Christianity": "✝",
        "Islam":       "☪",
        "Hinduism":    "🕉",
        "World":       "✦",
    }
    symbol = symbols.get(religion, "✦")
    try:
        font = _get_font(48, bold=False)
        draw.text((x, y), symbol, font=font, fill=color)
    except Exception:
        pass  # Symbol unicode có thể lỗi trên một số font


# ============================================================
# THUMBNAIL CHÍNH
# ============================================================

def create_thumbnail(
    image_path:  str,
    title:       str,
    religion:    str,
    output_path: str | Path,
    subtitle:    str = "",
) -> str:
    """
    Tạo thumbnail YouTube 1280x720.

    Args:
        image_path:  Ảnh nền (sẽ tự crop/resize)
        title:       Tiêu đề video (tự wrap)
        religion:    Tôn giáo để chọn màu
        output_path: Đường dẫn lưu file (.jpg)
        subtitle:    Dòng phụ nhỏ hơn (không bắt buộc)
        
    Returns:
        Đường dẫn thumbnail đã tạo
    """
    W, H = THUMB_WIDTH, THUMB_HEIGHT
    colors = RELIGION_COLORS.get(religion, RELIGION_COLORS["World"])
    primary   = colors["primary"]
    secondary = colors["secondary"]

    # ── 1. Load và resize ảnh nền ─────────────────────────
    bg = Image.open(image_path).convert("RGB")

    # Crop center để không méo hình
    bg_ratio    = bg.width / bg.height
    target_ratio = W / H
    if bg_ratio > target_ratio:
        new_w = int(bg.height * target_ratio)
        offset = (bg.width - new_w) // 2
        bg = bg.crop((offset, 0, offset + new_w, bg.height))
    else:
        new_h = int(bg.width / target_ratio)
        offset = (bg.height - new_h) // 2
        bg = bg.crop((0, offset, bg.width, offset + new_h))

    bg = bg.resize((W, H), Image.LANCZOS)

    # Tăng độ tương phản nhẹ
    bg = ImageEnhance.Contrast(bg).enhance(1.15)

    # ── 2. Gradient overlay ───────────────────────────────
    bg = _add_gradient_overlay(bg, primary, alpha=THUMB_OVERLAY_ALPHA)

    draw = ImageDraw.Draw(bg)

    # ── 3. Top bar màu chủ ────────────────────────────────
    draw.rectangle([(0, 0), (W, 8)], fill=primary)

    # ── 4. Channel badge (góc trên trái) ─────────────────
    badge_font = _get_font(22, bold=True)
    badge_text = f"  {CHANNEL_NAME}  "
    badge_w = 260
    badge_h = 40
    draw.rounded_rectangle([(40, 30), (40 + badge_w, 30 + badge_h)],
                             radius=6, fill=(*primary, 200))
    draw.text((48, 38), badge_text, font=badge_font, fill=(255, 255, 255))

    # ── 5. Decorative line ────────────────────────────────
    _add_decorative_bar(draw, H - 130, W, secondary)

    # ── 6. Title Text ─────────────────────────────────────
    title_font = _get_font(THUMB_FONT_SIZE_TITLE, bold=True)
    
    # Wrap title
    max_chars  = 30
    lines      = textwrap.wrap(title, width=max_chars)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:27] + "..."

    # Tính vị trí text (căn dưới)
    line_h   = THUMB_FONT_SIZE_TITLE + 12
    text_h   = len(lines) * line_h
    y_start  = H - text_h - 55

    for i, line in enumerate(lines):
        y = y_start + i * line_h
        # Shadow
        draw.text((62, y + 3), line, font=title_font, fill=(0, 0, 0, 180))
        # Main text
        draw.text((60, y), line, font=title_font, fill=(255, 255, 255))

    # ── 7. Subtitle / Tagline ─────────────────────────────
    if subtitle:
        sub_font = _get_font(THUMB_FONT_SIZE_SUBTITLE, bold=False)
        sub_text = subtitle[:55]
        draw.text((62, H - 46), sub_text, font=sub_font, fill=(*secondary, 220))

    # ── 8. Highlight accent (glow effect đơn giản) ───────
    # Vẽ đường ngang màu secondary phía trên title
    draw.rectangle([(60, y_start - 16), (180, y_start - 10)], fill=secondary)

    # ── 9. Religion symbol góc phải ───────────────────────
    _add_religion_symbol(draw, religion, W - 110, H - 120, secondary)

    # ── 10. Save JPEG tối ưu ─────────────────────────────
    output_path = Path(output_path)
    bg.save(str(output_path), "JPEG", quality=95, optimize=True)

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"Thumbnail đã tạo: {output_path.name} ({size_kb:.0f} KB)")
    return str(output_path)
