from __future__ import annotations

import contextlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .common import validate_readable_file


def _import_basic_pitch_inference() -> tuple[Any, Any]:
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            from basic_pitch import inference  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: basic-pitch. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    predict = getattr(inference, "predict", None)
    if predict is None:
        raise RuntimeError("basic-pitch import succeeded but predict() was not found.")
    default_model_path = getattr(inference, "ICASSP_2022_MODEL_PATH", None)
    return predict, default_model_path


def _import_pretty_midi() -> Any:
    try:
        import pretty_midi  # type: ignore
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: pretty_midi. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    return pretty_midi


def _run_basic_pitch_predict(predict: Any, audio_path: Path, model_path: Any) -> Any:
    audio = str(audio_path)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        if model_path is not None:
            try:
                return predict(audio, model_path)
            except TypeError as exc:
                if "positional argument" not in str(exc):
                    raise
                return predict(audio)
        return predict(audio)


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


def derive_pitch_output_path(audio_path: Path) -> Path:
    resolved = audio_path.expanduser().resolve()
    return resolved.parent / f"{resolved.stem}_pitches.json"


def derive_pitch_midi_output_path(pitch_json_path: Path) -> Path:
    resolved = pitch_json_path.expanduser().resolve()
    return resolved.with_suffix(".mid")


def _validate_output_target(output_path: Path) -> Path:
    resolved_output_path = output_path.expanduser().resolve()
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
    return resolved_output_path


def extract_note_pitches(audio_path: Path) -> dict[str, Any]:
    resolved_audio_path = validate_readable_file(audio_path)
    predict, default_model_path = _import_basic_pitch_inference()

    _, _, note_events = _run_basic_pitch_predict(
        predict=predict,
        audio_path=resolved_audio_path,
        model_path=default_model_path,
    )
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
    resolved_output_path = _validate_output_target(
        output_path
        if output_path is not None
        else derive_pitch_output_path(resolved_audio_path)
    )

    resolved_output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return resolved_output_path


def read_pitch_json(pitch_json_path: Path) -> dict[str, Any]:
    resolved_input_path = validate_readable_file(pitch_json_path)
    try:
        payload = json.loads(resolved_input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {resolved_input_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"Expected top-level JSON object in pitch file: {resolved_input_path}"
        )
    return payload


def write_pitch_midi(payload: dict[str, Any], output_midi_path: Path) -> Path:
    pretty_midi = _import_pretty_midi()
    resolved_output_path = _validate_output_target(output_midi_path)

    notes = payload.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ValueError("No notes found in pitch payload.")

    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=0, name="Transcribed Notes")

    for note_item in notes:
        if not isinstance(note_item, dict):
            continue
        try:
            pitch = int(note_item["pitch_midi"])
            start = float(note_item["start_time_ms"]) / 1000.0
            end = float(note_item["end_time_ms"]) / 1000.0
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start:
            continue

        pitch = max(0, min(127, pitch))
        note = pretty_midi.Note(
            velocity=100,
            pitch=pitch,
            start=start,
            end=end,
        )
        instrument.notes.append(note)

    if not instrument.notes:
        raise ValueError("No valid notes found to write MIDI.")

    midi.instruments.append(instrument)
    midi.write(str(resolved_output_path))
    return resolved_output_path
