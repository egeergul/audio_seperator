from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")


def _import_torch():
    try:
        import torch  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: torch. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return torch


def _import_whisper():
    try:
        import whisper  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: openai-whisper. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return whisper


def available_whisper_models() -> list[str]:
    whisper = _import_whisper()
    return sorted(whisper.available_models())


def resolve_device(device: str) -> str:
    torch = _import_torch()
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device not in {"cpu", "cuda"}:
        raise ValueError(f"Unsupported device: {device}")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested device 'cuda' but CUDA is not available.")
    return device


def validate_audio_path(audio_path: Path) -> None:
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.access(audio_path, os.R_OK):
        raise PermissionError(f"Audio file is not readable: {audio_path}")


def _split_sentence_text(text: str) -> list[str]:
    parts = [match.group(0).strip() for match in SENTENCE_PATTERN.finditer(text)]
    return [part for part in parts if part]


def _duration_proportional_splits(
    sentence_texts: list[str], start: float, end: float
) -> list[tuple[float, float]]:
    duration = max(0.0, end - start)
    if duration <= 0.0 or len(sentence_texts) == 1:
        return [(start, end)]

    weights = [max(1, len(re.sub(r"\s+", "", text))) for text in sentence_texts]
    total_weight = sum(weights)
    if total_weight <= 0:
        return [(start, end)]

    chunks: list[tuple[float, float]] = []
    cursor = start
    for idx, weight in enumerate(weights):
        if idx == len(weights) - 1:
            next_cursor = end
        else:
            next_cursor = cursor + (duration * (weight / total_weight))
        chunks.append((cursor, next_cursor))
        cursor = next_cursor
    return chunks


def segments_to_sentence_chunks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    next_index = 0

    for segment in segments:
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        text = str(segment.get("text", "")).strip()
        if not text:
            continue

        sentence_texts = _split_sentence_text(text)
        if len(sentence_texts) <= 1:
            chunks.append(
                {
                    "index": next_index,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": text,
                }
            )
            next_index += 1
            continue

        time_ranges = _duration_proportional_splits(sentence_texts, start, end)
        if len(time_ranges) != len(sentence_texts):
            chunks.append(
                {
                    "index": next_index,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": text,
                }
            )
            next_index += 1
            continue

        for sentence_text, (chunk_start, chunk_end) in zip(sentence_texts, time_ranges):
            chunks.append(
                {
                    "index": next_index,
                    "start": round(float(chunk_start), 3),
                    "end": round(float(chunk_end), 3),
                    "text": sentence_text,
                }
            )
            next_index += 1

    return chunks


def transcribe_audio(
    audio_path: Path, model_name: str, language: str | None, device: str
) -> dict[str, Any]:
    validate_audio_path(audio_path)
    whisper = _import_whisper()
    runtime_device = resolve_device(device)

    model = whisper.load_model(model_name, device=runtime_device)
    result = model.transcribe(str(audio_path), language=language)

    segments = result.get("segments") or []
    if not isinstance(segments, list):
        segments = []

    chunks = segments_to_sentence_chunks(segments)
    duration_seconds = float(
        max(
            [chunk["end"] for chunk in chunks],
            default=0.0,
        )
    )

    payload = {
        "source_audio": str(audio_path.resolve()),
        "model": model_name,
        "language": result.get("language") or language,
        "duration_seconds": round(duration_seconds, 3),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunks": chunks,
    }
    return payload


def write_transcription_json(audio_path: Path, payload: dict[str, Any]) -> Path:
    output_path = audio_path.resolve().parent / "transcription.json"
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_video_transcription_payload(audio_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    resolved_audio_path = audio_path.resolve()
    folder_path = resolved_audio_path.parent
    input_audio_file = resolved_audio_path.name

    # Prefer matching kareoke track when input is *_vocals.mp3 and file exists.
    preferred_audio_file = input_audio_file
    if input_audio_file.endswith("_vocals.mp3"):
        candidate = input_audio_file.replace("_vocals.mp3", "_kareoke.mp3")
        if (folder_path / candidate).is_file():
            preferred_audio_file = candidate

    base_name = resolved_audio_path.stem
    if base_name.endswith("_vocals"):
        base_name = base_name[: -len("_vocals")]
    output_video_path = folder_path / f"{base_name}.mp4"

    chunks = payload.get("chunks", [])
    content: list[dict[str, Any]] = []
    for chunk in chunks:
        start_seconds = float(chunk.get("start", 0.0))
        end_seconds = float(chunk.get("end", start_seconds))
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue

        start_ms = int(round(start_seconds * 1000))
        end_ms = int(round(end_seconds * 1000))
        if end_ms < start_ms:
            end_ms = start_ms

        content.append(
            {
                "start_time_ms": start_ms,
                "end_time_ms": end_ms,
                "text": text,
            }
        )

    return {
        "folder_path": str(folder_path),
        "audio_file": preferred_audio_file,
        "video_width": 1920,
        "video_height": 1080,
        "output_video_path": str(output_video_path),
        "content": content,
    }


def write_video_transcription_json(audio_path: Path, payload: dict[str, Any]) -> Path:
    output_path = audio_path.resolve().parent / "transcription_for_video.json"
    video_payload = build_video_transcription_payload(audio_path, payload)
    output_path.write_text(
        json.dumps(video_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
