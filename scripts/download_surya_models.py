"""Pre-download surya-ocr models to data/models/hf_cache."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_CACHE = REPO_ROOT / "data" / "models" / "hf_cache"
HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MODEL_CACHE_DIR", str(HF_CACHE))

print(f"Downloading surya-ocr models to: {HF_CACHE}")
print("This may take several minutes on first run (~500MB)...")

try:
    from surya.model.detection.model import (
        load_model as load_det,
        load_processor as load_det_proc,
    )
    from surya.model.recognition.model import load_model as load_rec
    from surya.model.recognition.processor import load_processor as load_rec_proc

    print("  Loading detection model...")
    load_det()
    load_det_proc()
    print("  Loading recognition model...")
    load_rec()
    load_rec_proc()
    print("surya-ocr models ready.")
except Exception as e:
    print(f"[ERROR] Failed to download surya-ocr models: {e}")
    sys.exit(1)
