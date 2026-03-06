from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    transcription_path: Path
    vocals_audio_path: Path
    kareoke_audio_path: Path
    video_width: int
    video_height: int
    output_video_path: Path
    content: list[CaptionItem]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _format_seconds(seconds: float) -> str:
    formatted = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return formatted or "0"


def check_video_prerequisites() -> None:
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "Missing required command: ffmpeg. Install ffmpeg and ensure it is on PATH."
        )
    if shutil.which("ffprobe") is None:
        raise EnvironmentError(
            "Missing required command: ffprobe. Install ffprobe and ensure it is on PATH."
        )


def _require_readable_file(path: Path, field_name: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{field_name} not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"{field_name} is not readable: {resolved}")
    return resolved


def _derive_run_name(folder_path: Path) -> str:
    run_name = folder_path.resolve().name.strip()
    if not run_name:
        raise ValueError(f"Could not derive run name from folder: {folder_path}")
    return run_name


def load_transcription_chunks(transcription_path: Path) -> list[CaptionItem]:
    if not transcription_path.is_file():
        raise FileNotFoundError(f"Transcription file not found: {transcription_path}")

    try:
        raw = json.loads(transcription_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Transcription file is not valid JSON: {transcription_path}"
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError("Transcription JSON top-level value must be an object.")

    chunks_raw = raw.get("chunks")
    if not isinstance(chunks_raw, list):
        raise ValueError("Transcription JSON must include a 'chunks' list.")

    content_items: list[CaptionItem] = []
    for idx, item in enumerate(chunks_raw):
        if not isinstance(item, dict):
            raise ValueError(f"'chunks[{idx}]' must be an object.")

        start_time_ms = item.get("start_time_ms")
        end_time_ms = item.get("end_time_ms")
        text = item.get("text")

        if not _is_int(start_time_ms) or start_time_ms < 0:
            raise ValueError(
                f"'chunks[{idx}].start_time_ms' must be a non-negative integer."
            )
        if not _is_int(end_time_ms) or end_time_ms < 0:
            raise ValueError(
                f"'chunks[{idx}].end_time_ms' must be a non-negative integer."
            )
        if start_time_ms >= end_time_ms:
            raise ValueError(
                f"'chunks[{idx}]' has invalid timing: start_time_ms must be < end_time_ms."
            )
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"'chunks[{idx}].text' must be a non-empty string.")

        content_items.append(
            CaptionItem(
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                text=text.strip(),
            )
        )

    return content_items


def build_video_spec(
    transcription_path: Path,
    vocals_audio_path: Path,
    kareoke_audio_path: Path,
    video_width: int,
    video_height: int,
    output_video_path: Path | None = None,
) -> VideoSpec:
    if not _is_int(video_width) or video_width <= 0:
        raise ValueError("video width must be an integer greater than 0.")
    if not _is_int(video_height) or video_height <= 0:
        raise ValueError("video height must be an integer greater than 0.")

    resolved_transcription_path = _require_readable_file(
        transcription_path, "Transcription file"
    )
    resolved_vocals_audio_path = _require_readable_file(vocals_audio_path, "Vocals audio")
    resolved_kareoke_audio_path = _require_readable_file(
        kareoke_audio_path, "Kareoke audio"
    )

    content = load_transcription_chunks(resolved_transcription_path)
    run_dir = resolved_transcription_path.parent
    run_name = _derive_run_name(run_dir)

    resolved_output_video_path = (
        output_video_path.expanduser().resolve()
        if output_video_path is not None
        else (run_dir / f"{run_name}.mp4").resolve()
    )

    return VideoSpec(
        transcription_path=resolved_transcription_path,
        vocals_audio_path=resolved_vocals_audio_path,
        kareoke_audio_path=resolved_kareoke_audio_path,
        video_width=video_width,
        video_height=video_height,
        output_video_path=resolved_output_video_path,
        content=content,
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


def _text_width(
    draw: Any, text: str, font: Any, stroke_width: int
) -> int:
    left, _, right, _ = draw.textbbox(
        (0, 0), text, font=font, stroke_width=stroke_width
    )
    return right - left


def _line_height(
    draw: Any, font: Any, stroke_width: int
) -> int:
    _, top, _, bottom = draw.textbbox(
        (0, 0), "Ag", font=font, stroke_width=stroke_width
    )
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
    from PIL import Image, ImageDraw

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


def build_ffmpeg_command(
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
        str(spec.kareoke_audio_path),
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


def create_video_from_transcription(spec: VideoSpec) -> Path:
    check_video_prerequisites()
    spec.output_video_path.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds = _probe_audio_duration_seconds(spec.kareoke_audio_path)

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
        cmd = build_ffmpeg_command(spec, duration_seconds, overlays)
        _run_command(cmd)

    return spec.output_video_path
