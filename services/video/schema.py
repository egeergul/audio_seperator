from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaptionItem:
    start_time_ms: int
    end_time_ms: int
    text: str


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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

