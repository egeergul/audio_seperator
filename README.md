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

## Model directory reference

Default model directory is now local project path:

- `./models/MDX`

Override (optional):

- `AUDIO_SEP_MODELS_DIR=/absolute/path/to/models python main.py`

The required model hashes remain:

- vocals: `499a6a6bf9da6d330235a1576007ddc0` (`Kim_Vocal_2.safetensors`)
- instrumental (used as kareoke): `a78fcc2e0ff8d575edd2c55add1eaa64` (`Kim_Inst.safetensors`)
