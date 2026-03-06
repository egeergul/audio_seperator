# Agent Handoff: Audio Separation + JSON Video CLI

This file is the project context summary for future AI agents.

## 1) Project goals

Build terminal-based tools that:

1. asks user for a YouTube URL,
2. asks user for a creation name,
3. creates an output folder for that run,
4. downloads source audio from YouTube,
5. separates audio into:
   - `<name>_vocals.mp3`
   - `<name>_kareoke.mp3`
6. creates lyric videos from a JSON spec:
   - black background video
   - input audio track stitched into MP4
   - timed caption overlays

The spelling `kareoke` is intentional and required.

## 2) Current implementation status

Implemented and runnable.

- Audio separation entry point: `main.py`
- Audio separation app logic: `app/pipeline.py`
- Config/constants: `app/config.py`
- JSON video entry point: `video_from_json.py`
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
├── video_from_json.py
├── requirements.txt
└── README.md
```

Output runs go to: `outputs/<creation_name>/`

## 6) Runtime flow (current)

### 6.1 Audio separation flow

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

### 6.2 JSON video flow

`run()` in `video_from_json.py`:

1. Parse CLI arg (`python video_from_json.py /path/to/spec.json`).
2. Validate spec JSON required keys and caption timing constraints.
3. Check prerequisites (`ffmpeg`, `ffprobe`) and verify audio path exists.
4. Probe audio duration via `ffprobe`.
5. Render one transparent PNG overlay per caption item with centered text.
6. Choose largest dynamic font size that fits most of frame area.
7. Run one `ffmpeg` command:
   - `color=black` base video with target width/height
   - overlay PNG captions by `enable=between(t,start,end)`
   - map audio + video to MP4 output
8. Emit output video path on success.

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
- `Pillow`

Why `torchcodec` and `packaging` matter:

- `torchaudio` in this environment uses TorchCodec backend for load/save.
- Missing `torchcodec` causes runtime crash in `torchaudio.load`.
- `safetensors.torch` imports `packaging`; missing it crashes model load.

Why `Pillow` matters:

- `video_from_json.py` uses Pillow to render caption text overlays.
- Missing `Pillow` prevents lyric video generation.

## 8) Known warnings / caveats

- `yt-dlp` may warn about missing JS runtime for some YouTube extractions.
- Current invalid-URL behavior: output folder may be created before download failure.
- On first separation run for each model, runtime can be slow.
- `video_from_json.py` requires a scalable TrueType font for large captions.
- Output key in video JSON prefers `output_video_path` but supports `video_path` alias.

## 9) How to run

```bash
source .venv/bin/activate
python main.py
```

Lyric video from JSON:

```bash
source .venv/bin/activate
python video_from_json.py /path/to/spec.json
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
- Keep `video_from_json.py` JSON contract stable unless user asks otherwise.
- Caption behavior is currently centered, high-visibility, and dynamically scaled by resolution.
