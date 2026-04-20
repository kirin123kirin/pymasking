"""Pre-download surya-ocr models to data/models/hf_cache."""

import inspect
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
    # surya >= 0.6: predictor-based API
    from surya.detection import DetectionPredictor
    from surya.recognition import RecognitionPredictor
    print("  Loading detection predictor...")
    det = DetectionPredictor()
    # Patch attributes missing from older model checkpoints (surya/issues/492)
    if hasattr(det, 'model') and hasattr(det.model, 'config') and not hasattr(det.model.config, 'bbox_size'):
        det.model.config.bbox_size = 4
    if not hasattr(det, 'tasks'):
        det.tasks = []
    print("  Loading recognition predictor...")
    rec_params = inspect.signature(RecognitionPredictor.__init__).parameters
    if "foundation_predictor" in rec_params:
        rec = RecognitionPredictor(det)
    else:
        rec = RecognitionPredictor()

    # Newer surya may download model weights lazily (only on first inference).
    # Force the download now by accessing rec.model, then fallback to a dummy call.
    print("  Ensuring recognition model weights are downloaded...")
    _forced = False
    try:
        m = rec.model  # triggers @cached_property / lazy download
        if m is not None:
            _forced = True
    except Exception:
        pass

    if not _forced:
        try:
            from PIL import Image
            dummy = Image.new("RGB", (64, 32), color=(255, 255, 255))
            try:
                rec([dummy], [["ja"]])
            except Exception:
                from surya.ocr import run_ocr
                run_ocr([dummy], [["ja"]], det, rec)
        except Exception as e:
            print(f"  [WARNING] Could not force recognition download: {e}")
except ImportError:
    # surya < 0.6: model/processor API
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
    except ImportError as e:
        print(f"[ERROR] Failed to download surya-ocr models: {e}")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to download surya-ocr models: {e}")
    sys.exit(1)

print("surya-ocr models ready.")
