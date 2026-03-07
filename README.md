# Audio Scraper CLI (Micro-Service Style)

This project is a script-first audio pipeline with 7 independent CLI commands that hand off files by path.

Canonical output root is:

- `.outputs/`

The `kareoke` spelling is intentional and part of the file contract.

## Requirements

- Python 3.10+ (for `basic-pitch`, use Python 3.11 or lower)
- `ffmpeg` and `ffprobe` on `PATH`

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick Start (End-to-End)

```bash
python3 create_folder.py "Wild Flower"
python3 scrape_audio.py "https://youtube.com/watch?v=..." "/absolute/path/to/.outputs/Wild_Flower"
python3 seperate_audio.py "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_original.mp3"
python3 extract_pitches.py "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3"
python3 transcribe_audio.py "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3" --model small --device auto
python3 create_video_from_transcription.py \
  "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_transcription.json" \
  "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3" \
  "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_kareoke.mp3"
python3 visualize_audio_wave.py "/absolute/path/to/.outputs/Wild_Flower/Wild_Flower_vocals.mp3"
```

## Script Reference

### 1) `create_folder.py`

Usage:

```bash
python3 create_folder.py <name>
```

Parameters:

- `name` (required): raw run name.

What it does:

- Normalizes name with `[^A-Za-z0-9._-] -> _` and trims leading/trailing `._-`.
- Creates `.outputs/<normalized_name>`.
- Fails if name becomes empty after sanitization or folder already exists.
- Prints the absolute created path.

Under the hood:

- Uses `services.folder.create_normalized_run_folder`.
- Path constants come from `services/config.py` (`OUTPUTS_DIR`).

### 2) `scrape_audio.py`

Usage:

```bash
python3 scrape_audio.py <youtube_url> <output_folder_path>
```

Parameters:

- `youtube_url` (required): YouTube video URL.
- `output_folder_path` (required): existing run folder path.

What it does:

- Validates non-empty URL and existing output folder.
- Derives `run_name` from folder basename.
- Downloads/extracts audio to:
  - `<output_folder_path>/<run_name>_original.mp3`
- Fails if expected output file is missing after download.

Under the hood:

- Calls `yt-dlp` through `python -m yt_dlp --no-playlist -x --audio-format mp3`.
- Implemented in `services.download.download_youtube_audio`.

### 3) `seperate_audio.py`

Usage:

```bash
python3 seperate_audio.py <original_file_path>
```

Parameters:

- `original_file_path` (required): readable source file, usually `<run_name>_original.mp3`.

What it does:

- Validates source file exists/readable.
- Derives `run_name` from parent folder name.
- Runs demix twice with fixed model hashes:
  - vocals: `499a6a6bf9da6d330235a1576007ddc0`
  - instrumental: `a78fcc2e0ff8d575edd2c55add1eaa64`
- Writes in same folder:
  - `<run_name>_vocals.mp3`
  - `<run_name>_kareoke.mp3`

Under the hood:

- Invokes vendored runtime `vendor/audio_separation/tool/demix.py` twice.
- Uses `--out_base <run_dir>/<run_name> --format mp3 --models_dir <...>`.
- Renames vendor outputs (`*_Vocals.mp3`, `*_Instrumental.mp3`) to required lowercase contract.

Model directory behavior:

- Default: `models/MDX`
- Optional override: `AUDIO_SEP_MODELS_DIR=/abs/path/to/models`

### 4) `transcribe_audio.py`

Usage:

```bash
python3 transcribe_audio.py <vocals_audio_path> [--model ...] [--language ...] [--device auto|cpu|cuda]
```

Parameters:

- `vocals_audio_path` (required): input vocals audio path.
- `--model` (optional, default `small`):
  - `tiny`, `tiny.en`, `base`, `base.en`, `small`, `small.en`, `medium`, `medium.en`, `large`, `large-v1`, `large-v2`, `large-v3`, `turbo`
- `--language` (optional): language code like `en`, `tr`. Omit for auto-detect.
- `--device` (optional, default `auto`): `auto`, `cpu`, `cuda`.

What it does:

- Runs Whisper transcription.
- Applies sentence chunking logic.
- Converts all chunk times to milliseconds.
- Writes:
  - `<run_name>_transcription.json`
- Does not create `transcription_for_video.json`.

Under the hood:

- `services.transcription.transcribe_audio` runs Whisper and builds payload.
- `services.transcription.segments_to_sentence_chunks_ms` handles punctuation-based split + proportional timing.
- `services.transcription.write_transcription_json` writes next to input audio.

Output schema:

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
      "text": "Lyric line"
    }
  ]
}
```

### 5) `create_video_from_transcription.py`

Usage:

```bash
python3 create_video_from_transcription.py \
  <transcription_json_path> \
  <vocals_audio_path> \
  <kareoke_audio_path> \
  [--width 1920] \
  [--height 1080] \
  [--output-video-path <path>]
```

Parameters:

- `transcription_json_path` (required): path to `<run_name>_transcription.json`.
- `vocals_audio_path` (required): vocals path (validated as readable; part of contract).
- `kareoke_audio_path` (required): kareoke path (used as muxed audio track).
- `--width` (optional, default `1920`): output width.
- `--height` (optional, default `1080`): output height.
- `--output-video-path` (optional): explicit output path.

Default output path:

- `<folder>/<run_name>.mp4` if `--output-video-path` is omitted.

What it does:

- Validates transcription JSON shape (`chunks[].start_time_ms`, `chunks[].end_time_ms`, `chunks[].text`).
- Renders caption PNG overlays with Pillow (centered, dynamic font sizing).
- Builds ffmpeg filter graph with `enable=between(t,start,end)` using ms timings.
- Produces black-background MP4 with kareoke audio.

Under the hood:

- `services.video.build_video_spec`
- `services.video.load_transcription_chunks`
- `services.video.build_ffmpeg_command`
- `services.video.create_video_from_transcription`

### 6) `visualize_audio_wave.py`

Usage:

```bash
python3 visualize_audio_wave.py <audio_path> [--output-image-path <path>] [--width 1920] [--height 400]
```

Parameters:

- `audio_path` (required): source audio file path (mp3/wav/etc. supported by ffmpeg).
- `--output-image-path` (optional): explicit output PNG path.
- `--width` (optional, default `1920`): output image width.
- `--height` (optional, default `400`): output image height.
- `--sample-rate` (optional, default `22050`): decode sample rate for waveform generation.
- `--background-color` (optional, default `#0B1020`): image background color.
- `--waveform-color` (optional, default `#38BDF8`): waveform color.
- `--center-line-color` (optional, default `#1E293B`): center axis line color.

Default output path:

- `<audio_folder>/<audio_stem>_waveform.png` if `--output-image-path` is omitted.

What it does:

- Validates source file and `ffmpeg` availability.
- Decodes source audio to mono PCM with ffmpeg.
- Computes per-column amplitude envelope.
- Renders a PNG waveform with Pillow.

Under the hood:

- `services.waveform.create_audio_waveform_image`

### 7) `extract_pitches.py`

Usage:

```bash
python3 extract_pitches.py <audio_path> [--output-json-path <path>]
```

Parameters:

- `audio_path` (required): source audio file path, typically `<run_name>_vocals.mp3`.
- `--output-json-path` (optional): explicit output JSON path.

Default output path:

- `<audio_folder>/<run_name>_pitches.json` if `--output-json-path` is omitted.

What it does:

- Validates source audio file exists/readable.
- Runs Basic Pitch inference and extracts note events.
- Normalizes note events to millisecond note items with MIDI, note name, and Hz.
- Writes the output JSON.

Under the hood:

- `services.pitch.extract_note_pitches`
- `services.pitch.write_pitch_json`

Output schema:

```json
{
  "source_audio": "/abs/path/to/<run_name>_vocals.mp3",
  "model": "basic-pitch",
  "created_at": "2026-03-07T00:00:00+00:00",
  "note_count": 2,
  "notes": [
    {
      "index": 0,
      "start_time_ms": 120,
      "end_time_ms": 680,
      "pitch_midi": 69,
      "note_name": "A4",
      "pitch_hz": 440.0
    }
  ]
}
```

## Output File Contract

Inside `.outputs/<run_name>/`:

- `<run_name>_original.mp3`
- `<run_name>_vocals.mp3`
- `<run_name>_kareoke.mp3`
- `<run_name>_transcription.json`
- `<run_name>_pitches.json` (when pitch extraction is used)
- `<run_name>.mp4` (default)
- `<audio_stem>_waveform.png` (when waveform visualization is used)

## Testing

There is currently no committed `tests/` directory in this checkout.

Recommended smoke checks:

```bash
python3 -m py_compile create_folder.py scrape_audio.py seperate_audio.py transcribe_audio.py create_video_from_transcription.py visualize_audio_wave.py extract_pitches.py services/*.py services/video/*.py
python3 create_folder.py --help
python3 scrape_audio.py --help
python3 seperate_audio.py --help
python3 transcribe_audio.py --help
python3 create_video_from_transcription.py --help
python3 visualize_audio_wave.py --help
python3 extract_pitches.py --help
```
