# Agent Handoff: Audio Scraper Service-Module Refactor

This document is the single-source context file for future AI agents. It is written so an agent can continue work without re-exploring the repository.

## 1) Current Snapshot

- Repository root: `audio_scraper/`
- Refactor status: `app/` package was removed and replaced by `services/`.
- Canonical output root is `.outputs/` (hidden).
- Spelling contract `kareoke` is intentionally preserved across scripts and outputs.
- Legacy interactive orchestrator (`main.py`) is removed.
- Full pipeline orchestrator is JSON-driven (`run_full_pipeline_w_json.py`).
- Legacy JSON-video entry script (`video_from_json.py`) is no longer used; video flow is handled by `create_video_from_transcription.py` + `services/video/*`.
- There is currently no committed `tests/` directory in this checkout.

## 2) Project Goals

The project provides a file-handoff pipeline of independent scripts:

1. Create a normalized run folder.
2. Download YouTube audio into that run folder.
3. Separate original audio into vocals + kareoke tracks.
4. Transcribe vocals into millisecond chunks.
5. Render MP4 with black background and timed captions, muxing kareoke audio.
6. Create video metadata text (title/description/tags/pin comment) for the vocals track.
7. Optionally render a waveform PNG from any audio input.
8. Optionally extract sung melody note events from audio with Basic Pitch.
9. Optionally convert pitch JSON into a MIDI file.

## 3) Public CLI Contracts (Implemented)

### `create_folder.py`

Command:

```bash
python3 create_folder.py <name>
```

Behavior:

- Sanitizes `<name>` with regex `[^A-Za-z0-9._-]+ -> _`, then trims leading/trailing `._-`.
- Fails if sanitized name is empty.
- Creates `.outputs/<normalized_name>`.
- Fails if target folder already exists.
- Prints absolute created folder path.

Backed by:

- `services.folder.sanitize_creation_name`
- `services.folder.create_run_folder`
- `services.folder.create_normalized_run_folder`

### `scrape_audio.py`

Command:

```bash
python3 scrape_audio.py <youtube_url> <output_folder_path>
```

Behavior:

- Validates URL is non-empty.
- Validates output folder exists and is a directory.
- Derives `run_name` from folder basename.
- Downloads and extracts audio via `yt-dlp` to `<run_name>_original.mp3`.
- Fails if expected MP3 does not exist after download.
- Prints absolute output audio path.

Backed by:

- `services.download.download_youtube_audio`

### `seperate_audio.py`

Command:

```bash
python3 seperate_audio.py <original_file_path>
```

Behavior:

- Validates input file exists and is readable.
- Derives `run_name` from parent folder basename.
- Runs vendor demix twice:
  - vocals hash: `499a6a6bf9da6d330235a1576007ddc0`
  - instrumental hash: `a78fcc2e0ff8d575edd2c55add1eaa64`
- Renames vendor outputs to:
  - `<run_name>_vocals.mp3`
  - `<run_name>_kareoke.mp3`
- Prints both output paths.

Backed by:

- `services.separation.seperate_audio`
- `services.separation.run_demix`
- `services.separation.rename_outputs_to_required_names`

### `transcribe_audio.py`

Command:

```bash
python3 transcribe_audio.py <vocals_audio_path> [--model ...] [--language ...] [--device auto|cpu|cuda]
```

Supported models:

- `tiny`, `tiny.en`, `base`, `base.en`, `small`, `small.en`, `medium`, `medium.en`, `large`, `large-v1`, `large-v2`, `large-v3`, `turbo`

Behavior:

- Validates input audio file exists/readable.
- Resolves device (`auto` => `cuda` if available else `cpu`).
- Runs Whisper transcription.
- Splits to sentence chunks and converts timing to ms.
- Writes only `<run_name>_transcription.json` in same folder.
- Does **not** generate `transcription_for_video.json`.

Backed by:

- `services.transcription.transcribe_audio`
- `services.transcription.segments_to_sentence_chunks_ms`
- `services.transcription.write_transcription_json`

### `create_video_from_transcription.py`

Command:

```bash
python3 create_video_from_transcription.py <transcription_json_path> <audio_path> [--width 1920] [--height 1080] [--output-video-path <path>]
```

Behavior:

- Validates transcription JSON format against ms-chunk schema.
- Validates audio path is readable.
- Uses provided `audio_path` as muxed output audio track.
- Uses chunk `start_time_ms`/`end_time_ms` to build ffmpeg overlay windows.
- Default output path: `<audio_stem>.mp4` beside transcription file.
- Generates black background + centered dynamic captions rendered via Pillow.

Backed by:

- `services.video.build_video_spec`
- `services.video.load_transcription_chunks`
- `services.video.create_video_from_transcription`
- `services.video.build_ffmpeg_command`

### `create_vocals_video_metadata.py`

Command:

```bash
python3 create_vocals_video_metadata.py <song_name> <artist_name> <folder_path> [--language en|tr]
```

Behavior:

- Validates the folder exists and finds `<run_name>_vocals.mp3` (or a single `*_vocals.mp3`).
- Generates a video metadata text file using the selected language template.
- Writes `<vocals_stem>_video_texts.txt` beside the vocals audio.
- Fails if output file already exists.

Backed by:

- `services.video_metadata.find_vocals_audio_in_folder`
- `services.video_metadata.create_video_metadata_for_vocals`

### `visualize_audio_wave.py`

Command:

```bash
python3 visualize_audio_wave.py <audio_path> [--output-image-path <path>] [--width 1920] [--height 400]
```

Behavior:

- Validates source audio path and ffmpeg availability.
- Decodes input audio to mono PCM (`s16le`) using ffmpeg.
- Builds a per-column amplitude envelope and renders PNG with Pillow.
- Default output path: `<audio_stem>_waveform.png` beside input audio.
- Fails if output file already exists.

Backed by:

- `services.waveform.create_audio_waveform_image`

### `extract_pitches.py`

Command:

```bash
python3 extract_pitches.py <audio_path> [--output-json-path <path>]
```

Behavior:

- Validates input audio file exists and is readable.
- Runs Basic Pitch inference and reads note events.
- Normalizes note events to ms-based note objects:
  - `index`, `start_time_ms`, `end_time_ms`, `pitch_midi`, `note_name`, `pitch_hz`
- Writes default output `<audio_stem>_pitches.json` beside input audio.
- Fails if output file already exists.

Backed by:

- `services.pitch.extract_note_pitches`
- `services.pitch.write_pitch_json`

### `convert_pitch_json_to_midi.py`

Command:

```bash
python3 convert_pitch_json_to_midi.py <pitch_json_path> [--output-midi-path <path>]
```

Behavior:

- Validates and loads pitch JSON input.
- Converts `notes[]` entries into MIDI notes.
- Writes default output `<pitch_json_stem>.mid` beside input JSON.
- Fails if output file already exists.

Backed by:

- `services.pitch.read_pitch_json`
- `services.pitch.write_pitch_midi`

### `run_full_pipeline_w_json.py`

Command:

```bash
python3 run_full_pipeline_w_json.py <config_json_path>
```

Behavior:

- Runs the same 6-step flow as the end-to-end commands.
- Reads all required values from a JSON config file (no interactive prompts).
- Optional fields default to: model `small`, device `auto`, video 1920x1080, metadata language `en`.
- Accepts `video_width`/`video_height` or `width`/`height`.

Example JSON:

```json
{
  "folder_name": "Wild Flower",
  "youtube_url": "https://youtube.com/watch?v=...",
  "model": "small",
  "language": "en",
  "device": "auto",
  "video_width": 1920,
  "video_height": 1080,
  "song_name": "Golden",
  "artist_name": "Harry Styles",
  "metadata_language": "en"
}
```

## 4) Data Contracts

### Run name derivation

- Run name always comes from parent folder basename.
- This applies to download output names, separation outputs, transcription output name, and default video output name.
- Pitch output names derive from input audio stem (for example: `golden_vocals.mp3` -> `golden_vocals_pitches.json` / `.mid`).

### Output naming contract

Inside `.outputs/<run_name>/`:

- `<run_name>_original.mp3`
- `<run_name>_vocals.mp3`
- `<run_name>_kareoke.mp3`
- `<run_name>_transcription.json`
- `<audio_stem>_pitches.json` (optional pitch extraction output)
- `<audio_stem>_pitches.mid` (optional pitch JSON to MIDI conversion output)
- `<audio_stem>.mp4` (default video output)
- `<audio_stem>_waveform.png` (optional waveform visualization output)
- `<vocals_stem>_video_texts.txt` (optional video metadata output)

### Transcription JSON schema (ms)

Produced by `transcribe_audio.py` and consumed by `create_video_from_transcription.py`:

```json
{
  "source_audio": "/abs/path/to/<run_name>_vocals.mp3",
  "model": "small",
  "language": "en",
  "duration_ms": 123456,
  "created_at": "2026-03-07T00:00:00+00:00",
  "chunks": [
    {
      "index": 0,
      "start_time_ms": 0,
      "end_time_ms": 1500,
      "text": "Line"
    }
  ]
}
```

Validation rules in `services.video.load_transcription_chunks`:

- top-level object with `chunks` list
- each chunk is object
- `start_time_ms` non-negative int
- `end_time_ms` non-negative int
- `start_time_ms < end_time_ms`
- `text` non-empty string

## 5) Architecture and Code Map

Top-level scripts are thin CLI wrappers only.

### Service modules

- `services/config.py`
  - source of truth for project paths and model hashes.
  - `OUTPUTS_DIR = PROJECT_ROOT / ".outputs"`
- `services/common.py`
  - shared command execution and path validation helpers.
- `services/folder.py`
  - folder creation and name sanitization.
- `services/download.py`
  - yt-dlp download orchestration.
- `services/separation.py`
  - separation prerequisites, demix orchestration, rename contract.
- `services/transcription.py`
  - whisper loading, device selection, sentence chunking, ms conversion, JSON writing.
- `services/pitch.py`
  - Basic Pitch inference + note-event normalization + JSON + MIDI writing.
- `services/waveform.py`
  - ffmpeg decode + waveform envelope rendering to PNG.
- `services/video_metadata.py`
  - video metadata template selection and file writing.
- `services/video/schema.py`
  - transcription JSON validation and caption item parsing.
- `services/video/spec.py`
  - video spec construction and output path derivation.
- `services/video/captions.py`
  - caption image layout/rendering.
- `services/video/ffmpeg.py`
  - ffprobe duration lookup, ffmpeg filter graph and command build/run.
- `services/video/service.py`
  - end-to-end video creation orchestration.

### Vendor integration boundary

- Demix entrypoint invoked by project code:
  - `vendor/audio_separation/tool/demix.py`
- Called through:
  - `services.separation.run_demix(...)`
- Working directory for invocation:
  - `vendor/audio_separation`

## 6) Vendored Audio Separation Runtime Details

Used runtime subset lives under `vendor/audio_separation/`.

Critical files for CLI demix path:

- `tool/demix.py`
- `tool/bootstrap/__init__.py`
- `src/nodes/...` (db, inference, utils)
- `models/uvr_model_data.json`

Demix CLI arguments currently passed by project:

- `-m <model_hash>`
- `--out_base <run_dir>/<run_name>`
- `--format mp3`
- `--models_dir <resolved_models_dir>`
- `<input_audio>`

Project intentionally does **not** pass `--save_complement`; it runs demix twice for explicit model hashes.

### Model location behavior

- Default model folder: `models/MDX`
- Override with env var `AUDIO_SEP_MODELS_DIR`
- If default folder missing, it is created.

Known local model cache files currently in repo working tree:

- `models/MDX/Kim_Vocal_2.safetensors`
- `models/MDX/Kim_Inst.safetensors`
- `models/Demucs/htdemucs_ft.safetensors`
- catalog files in `models/*/.catalog.csv` include hashes.

## 7) Dependencies and Runtime Requirements

From `requirements.txt`:

- `torch`
- `torchaudio`
- `torchcodec`
- `numpy`
- `safetensors`
- `packaging`
- `tqdm`
- `seconohe>=1.0.2`
- `yt-dlp`
- `Pillow`
- `openai-whisper`
- `basic-pitch`

System tools required:

- `ffmpeg`
- `ffprobe`

Notes:

- `services.separation.check_separation_prerequisites` explicitly checks `ffmpeg`, `torchcodec`, `packaging`.
- `services.video.check_video_prerequisites` checks `ffmpeg` and `ffprobe`.
- `services.waveform.check_waveform_prerequisites` checks `ffmpeg`.
- `basic-pitch` currently works with Python 3.11 or lower in this setup; Python 3.14 install fails due upstream dependency constraints.

## 8) Repository Layout (Relevant)

```text
audio_scraper/
├── services/
│   ├── __init__.py
│   ├── config.py
│   ├── common.py
│   ├── folder.py
│   ├── download.py
│   ├── separation.py
│   ├── transcription.py
│   ├── pitch.py
│   ├── waveform.py
│   ├── video_metadata.py
│   └── video/
│       ├── __init__.py
│       ├── schema.py
│       ├── spec.py
│       ├── captions.py
│       ├── ffmpeg.py
│       └── service.py
├── create_folder.py
├── scrape_audio.py
├── seperate_audio.py
├── transcribe_audio.py
├── extract_pitches.py
├── convert_pitch_json_to_midi.py
├── create_video_from_transcription.py
├── create_vocals_video_metadata.py
├── visualize_audio_wave.py
├── run_full_pipeline_w_json.py
├── vendor/audio_separation/
├── models/
├── .outputs/
├── requirements.txt
├── README.md
└── AGENT_HANDOFF.md
```

## 9) Known Caveats and Design Constraints

- `kareoke` spelling is intentional contract; do not normalize to `karaoke` unless explicitly requested.
- No overwrite mode: scripts fail on conflicting targets.
- `create_video_from_transcription.py` accepts one mux audio arg and derives default output from that audio stem.
- Whisper model downloads can cause first-run latency.
- Basic Pitch model download can cause first-run latency.
- Separation first-run latency can be high depending on model availability and hardware.
- Caption rendering needs a scalable TTF font (`DejaVuSans-Bold.ttf` or macOS Arial fallback paths).

## 10) Practical Command Sequence

```bash
python3 create_folder.py "Wild Flower"
python3 scrape_audio.py "https://youtube.com/watch?v=..." "/abs/path/to/.outputs/Wild_Flower"
python3 seperate_audio.py "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_original.mp3"
python3 extract_pitches.py "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3"
python3 convert_pitch_json_to_midi.py "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_vocals_pitches.json"
python3 transcribe_audio.py "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3" --model small --device auto
python3 create_video_from_transcription.py \
  "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_transcription.json" \
  "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_kareoke.mp3"
python3 visualize_audio_wave.py "/abs/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3"
python3 create_vocals_video_metadata.py "Golden" "Harry Styles" "/abs/path/to/.outputs/Wild_Flower" --language en
```

JSON-driven full pipeline alternative:

```bash
python3 run_full_pipeline_w_json.py "/abs/path/to/pipeline_config.json"
```

## 11) Recommendations for the Next Agent

1. Preserve service-layer boundaries (`services/separation.py`, `services/transcription.py`, `services/video/*`) and keep top-level scripts thin.
2. Keep `services/config.py` as the only path/hash constants source.
3. If modifying transcription schema, update both producer (`services/transcription.py`) and validator/consumer (`services/video/schema.py`) together.
4. If changing demix invocation, validate both model hashes still produce `*_Vocals.mp3` and `*_Instrumental.mp3` source files before rename.
5. Maintain `.outputs/` as canonical output root unless user requests a breaking change.
6. Run compile/help smoke checks after behavior changes.
7. For waveform changes, keep ffmpeg decode and Pillow render responsibilities in `services/waveform.py` (thin CLI wrapper only).
8. For pitch extraction changes, keep Basic Pitch-specific parsing and output normalization in `services/pitch.py` (thin CLI wrapper only).
