from __future__ import annotations

from pathlib import Path
from typing import Any

TEXT_MAX_WIDTH_RATIO = 0.92
TEXT_MAX_HEIGHT_RATIO = 0.78


def _load_font(font_size: int) -> Any:
    from PIL import ImageFont

    font_candidates = [
        "DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, font_size)
        except OSError:
            continue
    raise RuntimeError(
        "No scalable TrueType font found. Install a system TTF font for large captions."
    )


def _text_width(draw: Any, text: str, font: Any, stroke_width: int) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return right - left


def _line_height(draw: Any, font: Any, stroke_width: int) -> int:
    _, top, _, bottom = draw.textbbox((0, 0), "Ag", font=font, stroke_width=stroke_width)
    return bottom - top


def _split_long_token(
    draw: Any,
    token: str,
    font: Any,
    max_width: int,
    stroke_width: int,
) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in token:
        candidate = current + char
        if current and _text_width(draw, candidate, font, stroke_width) > max_width:
            parts.append(current)
            current = char
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts if parts else [token]


def _wrap_text(
    draw: Any,
    text: str,
    font: Any,
    max_width: int,
    stroke_width: int,
) -> list[str]:
    tokens = text.split()
    if not tokens:
        return [text]

    expanded_tokens: list[str] = []
    for token in tokens:
        if _text_width(draw, token, font, stroke_width) <= max_width:
            expanded_tokens.append(token)
            continue
        expanded_tokens.extend(_split_long_token(draw, token, font, max_width, stroke_width))

    lines: list[str] = []
    current = expanded_tokens[0]
    for token in expanded_tokens[1:]:
        candidate = f"{current} {token}"
        if _text_width(draw, candidate, font, stroke_width) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = token
    lines.append(current)
    return lines


def render_caption_image(
    output_path: Path, text: str, width: int, height: int, index: int
) -> Path:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    max_text_width = int(width * TEXT_MAX_WIDTH_RATIO)
    max_text_height = int(height * TEXT_MAX_HEIGHT_RATIO)

    low = 16
    high = max(low, min(width, height))
    best_font = _load_font(low)
    best_stroke = max(2, low // 10)
    best_line_gap = max(8, low // 4)
    best_lines = _wrap_text(draw, text, best_font, max_text_width, best_stroke)

    while low <= high:
        mid = (low + high) // 2
        font = _load_font(mid)
        stroke_width = max(2, mid // 10)
        line_gap = max(8, mid // 4)
        lines = _wrap_text(draw, text, font, max_text_width, stroke_width)
        line_height = _line_height(draw, font, stroke_width)
        block_height = len(lines) * line_height + (len(lines) - 1) * line_gap
        block_width = max(_text_width(draw, line, font, stroke_width) for line in lines)
        if block_width <= max_text_width and block_height <= max_text_height:
            best_font = font
            best_stroke = stroke_width
            best_line_gap = line_gap
            best_lines = lines
            low = mid + 1
        else:
            high = mid - 1

    line_height = _line_height(draw, best_font, best_stroke)
    block_height = len(best_lines) * line_height + (len(best_lines) - 1) * best_line_gap
    y = max(0, (height - block_height) // 2)

    for line in best_lines:
        text_w = _text_width(draw, line, best_font, best_stroke)
        x = (width - text_w) // 2
        draw.text(
            (x, y),
            line,
            font=best_font,
            fill=(255, 255, 255, 255),
            stroke_width=best_stroke,
            stroke_fill=(0, 0, 0, 255),
        )
        y += line_height + best_line_gap

    overlay_path = output_path / f"caption_{index:04d}.png"
    image.save(overlay_path)
    return overlay_path
