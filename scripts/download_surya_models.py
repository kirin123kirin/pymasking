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


def _apply_surya_compat_patches() -> None:
    """Monkey-patches for surya/transformers version mismatches."""
    import torch

    # 1. SuryaDecoderConfig missing pad_token_id: newer transformers raises
    #    AttributeError for absent config keys instead of returning None.
    try:
        from surya.common.surya.decoder.config import SuryaDecoderConfig
        if not hasattr(SuryaDecoderConfig, 'pad_token_id'):
            SuryaDecoderConfig.pad_token_id = 0
    except Exception:
        pass

    # 2. ROPE_INIT_FUNCTIONS missing "default": newer transformers removed the
    #    standard no-scaling RoPE entry; surya's Qwen2RotaryEmbedding uses it.
    try:
        from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS
        if "default" not in ROPE_INIT_FUNCTIONS:
            def _rope_default(config, device=None, seq_len=None, **kwargs):
                head_dim = getattr(
                    config, 'head_dim',
                    config.hidden_size // config.num_attention_heads,
                )
                base = float(getattr(config, 'rope_theta', 10000.0))
                inv_freq = 1.0 / (
                    base ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim)
                )
                if device is not None:
                    inv_freq = inv_freq.to(device)
                return inv_freq, 1.0
            ROPE_INIT_FUNCTIONS["default"] = _rope_default
    except Exception:
        pass

    # 3. SuryaModel missing post_init() call + outdated _tied_weights_keys format.
    #    transformers 5.x requires all_tied_weights_keys dict attribute and dict-format
    #    _tied_weights_keys; surya's tie_weights uses removed _tie_or_clone_weights helper.
    try:
        from surya.common.surya import SuryaModel
        if isinstance(getattr(SuryaModel, '_tied_weights_keys', None), list):
            SuryaModel._tied_weights_keys = {"lm_head.weight": "embedder.token_embed.weight"}
        if not getattr(SuryaModel.__init__, '__pymasking_patched__', False):
            _orig_surya_init = SuryaModel.__init__

            def _patched_surya_init(self, *args, **kwargs):
                _orig_surya_init(self, *args, **kwargs)
                if not hasattr(self, 'all_tied_weights_keys'):
                    self.all_tied_weights_keys = {
                        "lm_head.weight": "embedder.token_embed.weight",
                    }
            _patched_surya_init.__pymasking_patched__ = True
            SuryaModel.__init__ = _patched_surya_init

        def _patched_surya_tie_weights(self, missing_keys=None, recompute_mapping=True):
            try:
                self.lm_head.weight = self.embedder.token_embed.weight
                if missing_keys is not None:
                    missing_keys.discard("lm_head.weight")
            except Exception:
                pass
        SuryaModel.tie_weights = _patched_surya_tie_weights
    except Exception:
        pass


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
    _apply_surya_compat_patches()
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
