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


def validate_audio_path(audio_path: Path) -> Path:
    resolved = audio_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Audio file not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"Audio file is not readable: {resolved}")
    return resolved


def derive_run_name_from_audio(audio_path: Path) -> str:
    parent_name = audio_path.resolve().parent.name.strip()
    if not parent_name:
        raise ValueError(f"Could not derive run name from path: {audio_path}")
    return parent_name


def derive_transcription_output_path(audio_path: Path) -> Path:
    resolved = audio_path.resolve()
    run_name = derive_run_name_from_audio(resolved)
    return resolved.parent / f"{run_name}_transcription.json"


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


def _to_ms(seconds: float) -> int:
    return int(round(seconds * 1000))


def segments_to_sentence_chunks_ms(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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
                    "start_time_ms": _to_ms(start),
                    "end_time_ms": _to_ms(max(start, end)),
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
                    "start_time_ms": _to_ms(start),
                    "end_time_ms": _to_ms(max(start, end)),
                    "text": text,
                }
            )
            next_index += 1
            continue

        for sentence_text, (chunk_start, chunk_end) in zip(sentence_texts, time_ranges):
            chunk_start_ms = _to_ms(chunk_start)
            chunk_end_ms = _to_ms(chunk_end)
            if chunk_end_ms < chunk_start_ms:
                chunk_end_ms = chunk_start_ms
            chunks.append(
                {
                    "index": next_index,
                    "start_time_ms": chunk_start_ms,
                    "end_time_ms": chunk_end_ms,
                    "text": sentence_text,
                }
            )
            next_index += 1

    return chunks


def transcribe_audio(
    audio_path: Path, model_name: str, language: str | None, device: str
) -> dict[str, Any]:
    resolved_audio_path = validate_audio_path(audio_path)
    whisper = _import_whisper()
    runtime_device = resolve_device(device)

    model = whisper.load_model(model_name, device=runtime_device)
    result = model.transcribe(str(resolved_audio_path), language=language)

    segments = result.get("segments") or []
    if not isinstance(segments, list):
        segments = []

    chunks = segments_to_sentence_chunks_ms(segments)
    duration_ms = max([chunk["end_time_ms"] for chunk in chunks], default=0)

    payload = {
        "source_audio": str(resolved_audio_path),
        "model": model_name,
        "language": result.get("language") or language,
        "duration_ms": duration_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunks": chunks,
    }
    return payload


def write_transcription_json(audio_path: Path, payload: dict[str, Any]) -> Path:
    resolved_audio_path = audio_path.expanduser().resolve()
    output_path = derive_transcription_output_path(resolved_audio_path)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
