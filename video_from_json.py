#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

FPS = 30
TEXT_MAX_WIDTH_RATIO = 0.92
TEXT_MAX_HEIGHT_RATIO = 0.78


@dataclass(frozen=True)
class CaptionItem:
    start_time_ms: int
    end_time_ms: int
    text: str


@dataclass(frozen=True)
class VideoSpec:
    folder_path: Path
    audio_path: Path
    video_width: int
    video_height: int
    output_video_path: Path
    content: list[CaptionItem]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_non_empty_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string.")
    return value


def _require_positive_int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    if not _is_int(value) or value <= 0:
        raise ValueError(f"'{key}' must be an integer greater than 0.")
    return value


def _format_seconds(seconds: float) -> str:
    formatted = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return formatted or "0"


def _check_prerequisites() -> None:
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "Missing required command: ffmpeg. Install ffmpeg and ensure it is on PATH."
        )
    if shutil.which("ffprobe") is None:
        raise EnvironmentError(
            "Missing required command: ffprobe. Install ffprobe and ensure it is on PATH."
        )


def _probe_audio_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    duration_raw = result.stdout.strip()
    if not duration_raw:
        raise RuntimeError(f"ffprobe did not return duration for: {audio_path}")
    try:
        duration = float(duration_raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to parse audio duration '{duration_raw}' for: {audio_path}"
        ) from exc
    if duration <= 0:
        raise RuntimeError(f"Audio duration must be positive, got {duration}.")
    return duration


def _load_font(font_size: int) -> ImageFont.ImageFont:
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


def _text_width(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, stroke_width: int
) -> int:
    left, _, right, _ = draw.textbbox(
        (0, 0), text, font=font, stroke_width=stroke_width
    )
    return right - left


def _line_height(
    draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, stroke_width: int
) -> int:
    _, top, _, bottom = draw.textbbox(
        (0, 0), "Ag", font=font, stroke_width=stroke_width
    )
    return bottom - top


def _split_long_token(
    draw: ImageDraw.ImageDraw,
    token: str,
    font: ImageFont.ImageFont,
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
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
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
        expanded_tokens.extend(
            _split_long_token(draw, token, font, max_width, stroke_width)
        )

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


def _render_caption_image(
    output_path: Path, text: str, width: int, height: int, index: int
) -> Path:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    max_text_width = int(width * TEXT_MAX_WIDTH_RATIO)
    max_text_height = int(height * TEXT_MAX_HEIGHT_RATIO)

    # Find the largest readable font size that fits most of the frame.
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
        block_width = max(
            _text_width(draw, line, font, stroke_width) for line in lines
        )
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


def _load_video_spec(spec_path: Path) -> VideoSpec:
    if not spec_path.is_file():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    try:
        raw = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Spec file is not valid JSON: {spec_path}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Top-level JSON must be an object.")

    required_keys = [
        "folder_path",
        "audio_file",
        "video_width",
        "video_height",
        "content",
    ]
    for key in required_keys:
        if key not in raw:
            raise ValueError(f"Missing required key: '{key}'")

    folder_path = Path(_require_non_empty_str(raw, "folder_path"))
    audio_file_raw = Path(_require_non_empty_str(raw, "audio_file"))
    video_width = _require_positive_int(raw, "video_width")
    video_height = _require_positive_int(raw, "video_height")

    output_video_key = "output_video_path" if "output_video_path" in raw else "video_path"
    output_video_raw = raw.get(output_video_key)
    if output_video_raw is None:
        raise ValueError("Missing output path. Provide 'output_video_path' (or 'video_path').")
    if not isinstance(output_video_raw, str) or not output_video_raw.strip():
        raise ValueError(f"'{output_video_key}' must be a non-empty string.")

    content_raw = raw["content"]
    if not isinstance(content_raw, list):
        raise ValueError("'content' must be a list.")

    content_items: list[CaptionItem] = []
    for idx, item in enumerate(content_raw):
        if not isinstance(item, dict):
            raise ValueError(f"'content[{idx}]' must be an object.")

        if "start_time_ms" not in item or "end_time_ms" not in item or "text" not in item:
            raise ValueError(
                f"'content[{idx}]' must include 'start_time_ms', 'end_time_ms', and 'text'."
            )

        start_time_ms = item["start_time_ms"]
        end_time_ms = item["end_time_ms"]
        text = item["text"]

        if not _is_int(start_time_ms) or start_time_ms < 0:
            raise ValueError(f"'content[{idx}].start_time_ms' must be a non-negative integer.")
        if not _is_int(end_time_ms) or end_time_ms < 0:
            raise ValueError(f"'content[{idx}].end_time_ms' must be a non-negative integer.")
        if start_time_ms >= end_time_ms:
            raise ValueError(
                f"'content[{idx}]' has invalid timing: start_time_ms must be < end_time_ms."
            )
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"'content[{idx}].text' must be a non-empty string.")

        content_items.append(
            CaptionItem(start_time_ms=start_time_ms, end_time_ms=end_time_ms, text=text.strip())
        )

    audio_path = audio_file_raw if audio_file_raw.is_absolute() else folder_path / audio_file_raw
    output_video_path = Path(output_video_raw)

    if not folder_path.is_dir():
        raise FileNotFoundError(f"Folder path does not exist or is not a directory: {folder_path}")
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    return VideoSpec(
        folder_path=folder_path,
        audio_path=audio_path,
        video_width=video_width,
        video_height=video_height,
        output_video_path=output_video_path,
        content=content_items,
    )


def _build_ffmpeg_command(
    spec: VideoSpec, duration_seconds: float, overlays: list[Path]
) -> list[str]:
    color_input = (
        f"color=black:s={spec.video_width}x{spec.video_height}:"
        f"r={FPS}:d={_format_seconds(duration_seconds)}"
    )

    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        color_input,
        "-i",
        str(spec.audio_path),
    ]

    for overlay_path in overlays:
        cmd.extend(["-loop", "1", "-i", str(overlay_path)])

    if overlays:
        filter_parts: list[str] = []
        previous = "[0:v]"
        for idx, item in enumerate(spec.content):
            overlay_stream = f"[{idx + 2}:v]"
            output_stream = f"[v{idx + 1}]"
            start_s = _format_seconds(item.start_time_ms / 1000.0)
            end_s = _format_seconds(item.end_time_ms / 1000.0)
            filter_parts.append(
                f"{previous}{overlay_stream}overlay=x=0:y=0:"
                f"enable=between(t\\,{start_s}\\,{end_s}){output_stream}"
            )
            previous = output_stream

        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                previous,
                "-map",
                "1:a",
            ]
        )
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend(
        [
            "-t",
            _format_seconds(duration_seconds),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(spec.output_video_path),
        ]
    )

    return cmd


def _run_command(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("ffmpeg command failed. See logs above for details.") from exc


def run(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python video_from_json.py /path/to/spec.json", file=sys.stderr)
        return 2

    spec_path = Path(argv[1])
    try:
        _check_prerequisites()
        spec = _load_video_spec(spec_path)
        spec.output_video_path.parent.mkdir(parents=True, exist_ok=True)
        duration_seconds = _probe_audio_duration_seconds(spec.audio_path)

        with tempfile.TemporaryDirectory(prefix="video_overlays_") as tmp_dir:
            overlay_dir = Path(tmp_dir)
            overlays = [
                _render_caption_image(
                    overlay_dir,
                    item.text,
                    spec.video_width,
                    spec.video_height,
                    idx,
                )
                for idx, item in enumerate(spec.content)
            ]
            cmd = _build_ffmpeg_command(spec, duration_seconds, overlays)
            _run_command(cmd)

        print(f"Video created successfully: {spec.output_video_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
