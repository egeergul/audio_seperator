# Agent Handoff: Audio Separation CLI

This file is the project context summary for future AI agents.

## 1) Project goal

Build a terminal-based pipeline that:

1. asks user for a YouTube URL,
2. asks user for a creation name,
3. creates an output folder for that run,
4. downloads source audio from YouTube,
5. separates audio into:
   - `<name>_vocals.mp3`
   - `<name>_kareoke.mp3`

The spelling `kareoke` is intentional and required.

## 2) Current implementation status

Implemented and runnable.

- Entry point: `main.py`
- App logic: `app/pipeline.py`
- Config/constants: `app/config.py`
- Models are expected locally in `models/MDX` by default.

## 3) Important historical decisions

- We no longer clone full `set-soft/AudioSeparation` at runtime.
- We vendor only needed runtime files under `vendor/audio_separation`.
- Previous `third_party` clone was removed from active project usage.
- Pipeline runs AudioSeparation `demix.py` twice (vocals + instrumental hash), then renames outputs.
- We do **not** use `--save_complement`.

## 4) Audio separation backend details

Vendored subset location: `vendor/audio_separation/`

Kept files/folders:

- `tool/demix.py`
- `tool/bootstrap/`
- `src/` (runtime modules used by demix)
- `models/uvr_model_data.json`
- `LICENSE`

Model hashes in use:

- Vocals: `499a6a6bf9da6d330235a1576007ddc0` (`Kim_Vocal_2.safetensors`)
- Instrumental (for kareoke): `a78fcc2e0ff8d575edd2c55add1eaa64` (`Kim_Inst.safetensors`)

## 5) Folder conventions

Current project layout:

```text
audio_scraper/
├── app/
├── vendor/audio_separation/
├── models/
│   ├── MDX/
│   └── Demucs/
├── outputs/
├── main.py
├── requirements.txt
└── README.md
```

Output runs go to: `outputs/<creation_name>/`

## 6) Runtime flow (current)

`run_cli()` in `app/pipeline.py`:

1. Check prerequisites (`git`, `ffmpeg`, `torchcodec`, `packaging`).
2. Verify vendored runtime files exist.
3. Prompt URL + creation name.
4. Sanitize name for filesystem safety.
5. Create `outputs/<name>/`.
6. Download YouTube audio as `source_audio.wav` via `yt-dlp`.
7. Resolve model directory (default `models/MDX`, optional env override).
8. Run `demix.py` with vocals hash.
9. Run `demix.py` with instrumental hash.
10. Rename:
    - `<name>_Vocals.mp3` -> `<name>_vocals.mp3`
    - `<name>_Instrumental.mp3` -> `<name>_kareoke.mp3`

## 7) Dependency notes (important)

Current `requirements.txt` includes:

- `torch`
- `torchaudio`
- `torchcodec`
- `numpy`
- `safetensors`
- `packaging`
- `tqdm`
- `seconohe>=1.0.2`
- `yt-dlp`

Why `torchcodec` and `packaging` matter:

- `torchaudio` in this environment uses TorchCodec backend for load/save.
- Missing `torchcodec` causes runtime crash in `torchaudio.load`.
- `safetensors.torch` imports `packaging`; missing it crashes model load.

## 8) Known warnings / caveats

- `yt-dlp` may warn about missing JS runtime for some YouTube extractions.
- Current invalid-URL behavior: output folder may be created before download failure.
- On first separation run for each model, runtime can be slow.

## 9) How to run

```bash
source .venv/bin/activate
python main.py
```

Optional model override:

```bash
AUDIO_SEP_MODELS_DIR=/absolute/path/to/mdx_models python main.py
```

## 10) Guidance for future agents

- Prefer keeping `app/config.py` as source of truth for paths and model hashes.
- Keep output naming contract unchanged unless user explicitly requests changes.
- If changing backend files, ensure `vendor/audio_separation/models/uvr_model_data.json` remains compatible.
- Do not reintroduce full repo clone flow unless explicitly requested.
