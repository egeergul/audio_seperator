from __future__ import annotations

import contextlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .common import validate_readable_file


def _import_basic_pitch_predict():
    try:
        from basic_pitch.inference import predict  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: basic-pitch. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return predict


def _midi_to_note_name(pitch_midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (pitch_midi // 12) - 1
    note_name = names[pitch_midi % 12]
    return f"{note_name}{octave}"


def _midi_to_hz(pitch_midi: int) -> float:
    return round(440.0 * (2.0 ** ((pitch_midi - 69) / 12.0)), 3)


def _seconds_to_ms(seconds: float) -> int:
    return int(round(seconds * 1000))


def _coerce_event_fields(event: Any) -> tuple[float, float, int] | None:
    start: Any = None
    end: Any = None
    pitch: Any = None

    if isinstance(event, dict):
        start = event.get("start_time_s", event.get("start_time_seconds", event.get("start")))
        end = event.get("end_time_s", event.get("end_time_seconds", event.get("end")))
        pitch = event.get(
            "pitch_midi",
            event.get("pitch", event.get("note")),
        )
    elif isinstance(event, Sequence) and not isinstance(event, (str, bytes)):
        if len(event) < 3:
            return None
        start = event[0]
        end = event[1]
        pitch = event[2]
    else:
        return None

    try:
        start_f = float(start)
        end_f = float(end)
        pitch_i = int(round(float(pitch)))
    except (TypeError, ValueError):
        return None

    if start_f < 0:
        start_f = 0.0
    if end_f <= start_f:
        return None
    if pitch_i < 0 or pitch_i > 127:
        return None
    return start_f, end_f, pitch_i


def _normalize_note_events(note_events: Any) -> list[dict[str, Any]]:
    if not isinstance(note_events, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_event in note_events:
        coerced = _coerce_event_fields(raw_event)
        if coerced is None:
            continue
        start_s, end_s, pitch_midi = coerced
        normalized.append(
            {
                "start_time_ms": _seconds_to_ms(start_s),
                "end_time_ms": _seconds_to_ms(end_s),
                "pitch_midi": pitch_midi,
                "note_name": _midi_to_note_name(pitch_midi),
                "pitch_hz": _midi_to_hz(pitch_midi),
            }
        )

    normalized.sort(key=lambda n: (n["start_time_ms"], n["end_time_ms"], n["pitch_midi"]))
    for idx, note in enumerate(normalized):
        note["index"] = idx
    return normalized


def derive_run_name_from_audio(audio_path: Path) -> str:
    parent_name = audio_path.resolve().parent.name.strip()
    if not parent_name:
        raise ValueError(f"Could not derive run name from path: {audio_path}")
    return parent_name


def derive_pitch_output_path(audio_path: Path) -> Path:
    resolved = audio_path.expanduser().resolve()
    run_name = derive_run_name_from_audio(resolved)
    return resolved.parent / f"{run_name}_pitches.json"


def extract_note_pitches(audio_path: Path) -> dict[str, Any]:
    resolved_audio_path = validate_readable_file(audio_path)
    predict = _import_basic_pitch_predict()

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        _, _, note_events = predict(str(resolved_audio_path))
    notes = _normalize_note_events(note_events)

    return {
        "source_audio": str(resolved_audio_path),
        "model": "basic-pitch",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note_count": len(notes),
        "notes": notes,
    }


def write_pitch_json(
    audio_path: Path, payload: dict[str, Any], output_path: Path | None = None
) -> Path:
    resolved_audio_path = audio_path.expanduser().resolve()
    resolved_output_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else derive_pitch_output_path(resolved_audio_path)
    )
    if resolved_output_path.exists():
        raise FileExistsError(f"Output file already exists: {resolved_output_path}")
    if not resolved_output_path.parent.is_dir():
        raise FileNotFoundError(
            f"Output folder does not exist: {resolved_output_path.parent}"
        )
    if not os.access(resolved_output_path.parent, os.W_OK):
        raise PermissionError(
            f"Output folder is not writable: {resolved_output_path.parent}"
        )

    resolved_output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return resolved_output_path
