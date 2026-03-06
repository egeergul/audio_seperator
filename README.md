# Audio Scraper + Separation CLI

Terminal-based Python pipeline that:

1. asks for a YouTube URL,
2. asks for a creation name,
3. creates `./<creation_name>/`,
4. downloads audio into that folder,
5. separates and exports:
   - `<name>_vocals.mp3`
   - `<name>_kareoke.mp3`

It uses [set-soft/AudioSeparation](https://github.com/set-soft/AudioSeparation) models via `tool/demix.py`.

## Prerequisites

- Python 3.10+
- `ffmpeg` on PATH
- `git` on PATH
- `torchcodec` Python package (included in `requirements.txt`)
- `packaging` Python package (included in `requirements.txt`)

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

## Model Directory Behavior

The script auto-detects models in this order:

1. `AUDIO_SEP_MODELS_DIR` (if set)
2. `~/Documents/ComfyUI/models/audio/MDX`
3. `~/Documents/ComfyUI/models`

If no directory is detected, `AudioSeparation` will download needed models into its own repo folder.
If a directory is detected but one of the required models is missing, only the missing model is downloaded.

## Notes

- On first run, if `third_party/AudioSeparation` is missing, it is cloned automatically.
- Output spelling follows your requirement: `kareoke`.
