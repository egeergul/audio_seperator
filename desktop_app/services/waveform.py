from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .common import validate_readable_file


def _import_numpy() -> Any:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: numpy. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return np


def _import_pillow() -> tuple[Any, Any, Any]:
    try:
        from PIL import Image, ImageColor, ImageDraw  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: Pillow. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return Image, ImageColor, ImageDraw


def check_waveform_prerequisites() -> None:
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "Missing required command: ffmpeg. Install ffmpeg and ensure it is on PATH."
        )


def derive_default_waveform_output_path(audio_path: Path) -> Path:
    resolved = audio_path.expanduser().resolve()
    return resolved.parent / f"{resolved.stem}_waveform.png"


def _decode_audio_to_mono_pcm(audio_path: Path, sample_rate: int) -> bytes:
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Failed to decode audio with ffmpeg: {stderr or 'unknown ffmpeg error'}"
        ) from exc
    if not result.stdout:
        raise RuntimeError("Decoded audio stream is empty.")
    return result.stdout


def _build_amplitude_envelope(np: Any, samples: Any, width: int) -> Any:
    if samples.size == 0:
        raise ValueError("No audio samples found.")

    chunk_size = int(np.ceil(samples.size / width))
    amplitudes = np.zeros(width, dtype=np.float32)
    for x in range(width):
        start = x * chunk_size
        if start >= samples.size:
            break
        end = min(start + chunk_size, samples.size)
        chunk = samples[start:end]
        amplitudes[x] = float(np.max(np.abs(chunk)))
    return amplitudes


def _validate_dimensions(width: int, height: int) -> None:
    if width <= 0:
        raise ValueError("Width must be a positive integer.")
    if height <= 0:
        raise ValueError("Height must be a positive integer.")


def _validate_sample_rate(sample_rate: int) -> None:
    if sample_rate <= 0:
        raise ValueError("Sample rate must be a positive integer.")


def create_audio_waveform_image(
    audio_path: Path,
    output_image_path: Path | None = None,
    *,
    width: int = 1920,
    height: int = 400,
    sample_rate: int = 22050,
    background_color: str = "#0B1020",
    waveform_color: str = "#38BDF8",
    center_line_color: str = "#1E293B",
) -> Path:
    _validate_dimensions(width, height)
    _validate_sample_rate(sample_rate)

    check_waveform_prerequisites()
    np = _import_numpy()
    Image, ImageColor, ImageDraw = _import_pillow()
    resolved_audio_path = validate_readable_file(audio_path)

    resolved_output = (
        output_image_path.expanduser().resolve()
        if output_image_path is not None
        else derive_default_waveform_output_path(resolved_audio_path)
    )
    if resolved_output.exists():
        raise FileExistsError(f"Output image already exists: {resolved_output}")
    if not resolved_output.parent.is_dir():
        raise FileNotFoundError(
            f"Output folder does not exist: {resolved_output.parent}"
        )

    pcm = _decode_audio_to_mono_pcm(resolved_audio_path, sample_rate=sample_rate)
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    amplitudes = _build_amplitude_envelope(np, samples, width=width)

    image = Image.new(
        "RGB",
        (width, height),
        color=ImageColor.getrgb(background_color),
    )
    draw = ImageDraw.Draw(image)
    center_y = height // 2
    draw.line(
        [(0, center_y), (width - 1, center_y)],
        fill=ImageColor.getrgb(center_line_color),
        width=1,
    )

    max_half_height = max(1, (height // 2) - 2)
    wave_rgb = ImageColor.getrgb(waveform_color)
    for x, amplitude in enumerate(amplitudes):
        half_bar = int(round(amplitude * max_half_height))
        if half_bar <= 0:
            continue
        draw.line(
            [(x, center_y - half_bar), (x, center_y + half_bar)],
            fill=wave_rgb,
            width=1,
        )

    image.save(resolved_output, format="PNG")
    return resolved_output
