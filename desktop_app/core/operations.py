from __future__ import annotations

from pathlib import Path

from services.download import download_youtube_audio
from services.folder import create_normalized_run_folder
from services.pitch import (
    derive_pitch_midi_output_path,
    derive_pitch_output_path,
    extract_note_pitches,
    read_pitch_json,
    write_pitch_json,
    write_pitch_midi,
)
from services.separation import seperate_audio
from services.transcription import transcribe_audio, write_transcription_json
from services.video import build_video_spec, create_video_from_transcription
from services.video_metadata import create_video_metadata_for_vocals
from services.waveform import create_audio_waveform_image
from services.youtube_upload import upload_video_to_youtube


def op_create_folder(folder_name: str) -> Path:
    run_dir = create_normalized_run_folder(folder_name)
    print(f"Created: {run_dir}")
    return run_dir


def op_download(youtube_url: str, output_folder: str) -> Path:
    path = download_youtube_audio(youtube_url, Path(output_folder))
    print(f"Downloaded: {path}")
    return path


def op_separate(original_audio_path: str) -> tuple[Path, Path]:
    vocals, kareoke = seperate_audio(Path(original_audio_path))
    print(f"Vocals: {vocals}")
    print(f"Kareoke: {kareoke}")
    return vocals, kareoke


def op_transcribe(
    audio_path: str, model: str, language: str, device: str
) -> Path:
    lang = language.strip() if language.strip() else None
    payload = transcribe_audio(
        audio_path=Path(audio_path),
        model_name=model,
        language=lang,
        device=device,
    )
    result_path = write_transcription_json(Path(audio_path), payload)
    print(f"Transcription: {result_path}")
    return result_path


def op_create_video(
    transcription_path: str, audio_path: str, width: int, height: int
) -> Path:
    spec = build_video_spec(
        transcription_path=Path(transcription_path),
        mux_audio_path=Path(audio_path),
        video_width=width,
        video_height=height,
        output_video_path=None,
    )
    video_path = create_video_from_transcription(spec)
    print(f"Video: {video_path}")
    return video_path


def op_create_metadata(
    vocals_audio_path: str, song_name: str, artist_name: str, language: str
) -> Path:
    metadata_path = create_video_metadata_for_vocals(
        vocals_audio_path=Path(vocals_audio_path),
        song_name=song_name,
        artist_name=artist_name,
        language=language,
    )
    print(f"Metadata: {metadata_path}")
    return metadata_path


def op_extract_pitches(audio_path: str) -> Path:
    payload = extract_note_pitches(Path(audio_path))
    output_path = derive_pitch_output_path(Path(audio_path))
    result = write_pitch_json(Path(audio_path), payload)
    print(f"Pitches: {result} ({payload['note_count']} notes)")
    return result


def op_convert_to_midi(pitch_json_path: str) -> Path:
    payload = read_pitch_json(Path(pitch_json_path))
    output_midi = derive_pitch_midi_output_path(Path(pitch_json_path))
    result = write_pitch_midi(payload, output_midi)
    print(f"MIDI: {result} ({len(payload.get('notes', []))} notes)")
    return result


def op_visualize_waveform(audio_path: str, width: int, height: int) -> Path:
    result = create_audio_waveform_image(
        audio_path=Path(audio_path),
        width=width,
        height=height,
    )
    print(f"Waveform: {result}")
    return result


def op_upload_youtube(
    video_path: str, metadata_path: str, privacy_status: str
) -> str:
    video_id = upload_video_to_youtube(
        video_file_path=Path(video_path),
        metadata_text_path=Path(metadata_path),
        privacy_status=privacy_status,
    )
    print(f"YouTube video ID: {video_id}")
    print(f"YouTube URL: https://www.youtube.com/watch?v={video_id}")
    return video_id
