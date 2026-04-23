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

    # RecognitionPredictor requires FoundationPredictor, NOT DetectionPredictor.
    # Passing DetectionPredictor caused processor.image_processor AttributeError at inference.
    print("  Loading recognition predictor (via FoundationPredictor)...")
    try:
        from surya.foundation import FoundationPredictor
        rec = RecognitionPredictor(FoundationPredictor())
    except (ImportError, TypeError):
        rec = RecognitionPredictor()

    # Newer surya may download model weights lazily (only on first inference).
    # Force the download now: try model attribute access, then a dummy inference call.
    # Note: surya >= 0.6 removed surya.ocr; use predictor directly.
    print("  Ensuring recognition model weights are downloaded...")
    _forced = False

    # Try various attribute names for the underlying model object
    for _attr in ("model", "recognition_model", "_model"):
        try:
            m = getattr(rec, _attr, None)
            if m is not None:
                _forced = True
                break
        except Exception:
            pass

    if not _forced:
        try:
            from PIL import Image
            dummy = Image.new("RGB", (64, 32), color=(255, 255, 255))
            # Call predictor directly (surya >= 0.6 API; surya.ocr removed)
            try:
                rec([dummy], [["ja"]])
                _forced = True
            except Exception:
                pass
            # If still not forced, try the full OCR pipeline via det + rec
            if not _forced:
                try:
                    det_result = det([dummy])
                    if det_result and det_result[0].bboxes:
                        from PIL import Image as _PIL
                        crops = [dummy.crop(tuple(int(v) for v in b.bbox))
                                 for b in det_result[0].bboxes[:1]]
                        rec(crops, [["ja"]])
                    _forced = True
                except Exception:
                    pass
        except Exception as e:
            print(f"  [WARNING] Could not force recognition download: {e}")

    if not _forced:
        print("  [WARNING] Recognition model download could not be verified; "
              "it will be downloaded on first use.")
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
