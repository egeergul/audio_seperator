# Audio Separation CLI

For agent-oriented project context and implementation history, see `AGENT_HANDOFF.md`.

Terminal-based Python pipeline that:

1. asks for a YouTube URL,
2. asks for a creation name,
3. creates a folder with that name under `outputs/`,
4. downloads source audio,
5. generates:
   - `<name>_vocals.mp3`
   - `<name>_kareoke.mp3`

It uses vendored runtime files from `set-soft/AudioSeparation` (only required files, not full repo clone).

## Project structure

```text
audio_scraper/
├── app/
│   ├── config.py
│   └── pipeline.py
├── vendor/
│   └── audio_separation/      # minimal runtime subset (tool/, src/, models db)
├── models/
│   ├── MDX/
│   └── Demucs/
├── outputs/
├── main.py
└── requirements.txt
```

## Prerequisites

- Python 3.10+
- `ffmpeg` on PATH
- `git` on PATH

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python main.py
```

## JSON To Video

Create a lyric video from a JSON spec:

```bash
source .venv/bin/activate
python video_from_json.py /path/to/spec.json
```

Expected JSON shape:

```json
{
  "folder_path": "outputs/wild_flower",
  "audio_file": "wild_flower_kareoke.mp3",
  "video_width": 1920,
  "video_height": 1080,
  "output_video_path": "outputs/wild_flower/wild_flower.mp4",
  "content": [
    {
      "start_time_ms": 0,
      "end_time_ms": 10000,
      "text": "Lyrics part 1"
    },
    {
      "start_time_ms": 12500,
      "end_time_ms": 15000,
      "text": "Lyrics part 2"
    }
  ]
}
```

Notes:

- `output_video_path` is preferred; `video_path` is also supported.
- `audio_file` is resolved relative to `folder_path` unless it is an absolute path.
- Captions are centered and dynamically scaled to occupy most of the frame.
- Output is black background video with timed lyrics and original audio.

## Transcribe Vocals (Whisper)

Generate two files next to an audio file:

- `transcription.json`
- `transcription_for_video.json` (compatible with `video_from_json.py`)

```bash
source .venv/bin/activate
python3 transcribe_audio.py /path/to/file_vocals.mp3
```

Optional flags:

- `--model` (default: `small`)
- `--language` (force language code, e.g. `en`, `tr`)
- `--device` (`auto`, `cpu`, `cuda`; default: `auto`)

Output JSON shape:

```json
{
  "source_audio": "/abs/path/to/file_vocals.mp3",
  "model": "small",
  "language": "en",
  "duration_seconds": 202.0,
  "created_at": "2026-03-06T21:49:34.472838+00:00",
  "chunks": [
    { "index": 0, "start": 0.0, "end": 2.0, "text": "Sentence one." },
    { "index": 1, "start": 2.0, "end": 5.4, "text": "Sentence two." }
  ]
}
```

Notes:

- Both JSON files are always written to the same folder as the input audio.
- Segments are sentence-oriented when punctuation (`.`, `!`, `?`) is available.
- Whisper model files are auto-downloaded on first use.

## Model directory reference

Default model directory is now local project path:

- `./models/MDX`

Override (optional):

- `AUDIO_SEP_MODELS_DIR=/absolute/path/to/models python main.py`

The required model hashes remain:

- vocals: `499a6a6bf9da6d330235a1576007ddc0` (`Kim_Vocal_2.safetensors`)
- instrumental (used as kareoke): `a78fcc2e0ff8d575edd2c55add1eaa64` (`Kim_Inst.safetensors`)
