from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / ".outputs"
LOCAL_MODELS_MDX_DIR = PROJECT_ROOT / "models" / "MDX"
VENDOR_AUDIO_SEPARATION_DIR = PROJECT_ROOT / "vendor" / "audio_separation"
VENDOR_DEMIX_SCRIPT = VENDOR_AUDIO_SEPARATION_DIR / "tool" / "demix.py"
VENDOR_MODELS_DB_JSON = VENDOR_AUDIO_SEPARATION_DIR / "models" / "uvr_model_data.json"

VOCALS_MODEL_HASH = "499a6a6bf9da6d330235a1576007ddc0"
INSTRUMENTAL_MODEL_HASH = "a78fcc2e0ff8d575edd2c55add1eaa64"
OUTPUT_FORMAT = "mp3"

