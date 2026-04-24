"""画像ファイルの視覚的マスキング処理（surya-ocr で検出 → 黒塗り）。"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from ..detector import detect_all, resolve_overlaps
from . import make_output_path

_log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_HF_CACHE = _REPO_ROOT / "data" / "models" / "hf_cache"

_det_model = None
_det_processor = None
_rec_model = None
_rec_processor = None
_surya_new_api = None  # True = predictor-based (>=0.6), False = model/processor (<0.6)


def _ensure_hf_home() -> None:
    _HF_CACHE.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MODEL_CACHE_DIR", str(_HF_CACHE))
    # Lower detection thresholds so weak/low-contrast text is not dropped.
    # surya defaults: TEXT=0.6, BLANK=0.35.  Dynamic scaling clamps at 0.15 floor
    # for text_threshold and 0.1 for low_text, so setting these low has a real effect.
    os.environ.setdefault("DETECTOR_TEXT_THRESHOLD", "0.2")
    os.environ.setdefault("DETECTOR_BLANK_THRESHOLD", "0.1")


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

    # 4. Qwen2_5_VisionRotaryEmbedding stores inv_freq as a plain attribute (not a
    #    registered buffer).  When transformers 5.x creates the model on the "meta"
    #    device for lazy loading, inv_freq becomes a meta tensor and is never moved
    #    to CPU by model.to(device).  Recompute on first forward call if on meta.
    try:
        from surya.common.surya.encoder import (  # noqa: F401
            Qwen2_5_VisionRotaryEmbedding as _VRot,
        )
        if not getattr(_VRot.__init__, '__pymasking_patched__', False):
            _orig_vrot_init = _VRot.__init__

            def _patched_vrot_init(self, dim: int, theta: float = 10000.0) -> None:
                _orig_vrot_init(self, dim, theta)
                self._rot_dim = dim
                self._rot_theta = theta
            _patched_vrot_init.__pymasking_patched__ = True
            _VRot.__init__ = _patched_vrot_init

        def _patched_vrot_forward(self, seqlen: int):
            inv_freq = self.inv_freq
            if hasattr(inv_freq, 'device') and inv_freq.device.type == 'meta':
                dim = getattr(self, '_rot_dim', inv_freq.shape[0] * 2)
                theta = getattr(self, '_rot_theta', 10000.0)
                inv_freq = 1.0 / (theta ** (
                    torch.arange(0, dim, 2, dtype=torch.float32) / dim
                ))
                self.inv_freq = inv_freq
            seq = torch.arange(seqlen, device='cpu', dtype=inv_freq.dtype)
            return torch.outer(seq, inv_freq)
        _VRot.forward = _patched_vrot_forward
    except Exception:
        pass


def preload_models() -> None:
    """Public entry point to eagerly load OCR models (call at app/CLI startup)."""
    _load_models()


def _load_models() -> None:
    global _det_model, _det_processor, _rec_model, _rec_processor, _surya_new_api
    if _det_model is not None and _surya_new_api is not None:
        return
    _ensure_hf_home()
    print("[surya] OCRモデルをローカルキャッシュから読み込み中 (インターネット接続不要)...", flush=True)
    # surya >= 0.6: predictor-based API
    try:
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor

        _det_model = DetectionPredictor()
        # Patch attributes missing from older model checkpoints (surya/issues/492)
        if hasattr(_det_model, 'model') and hasattr(_det_model.model, 'config'):
            cfg = _det_model.model.config
            if not hasattr(cfg, 'bbox_size'):
                cfg.bbox_size = 4

        # RecognitionPredictor requires FoundationPredictor (not DetectionPredictor).
        # Passing DetectionPredictor caused processor.image_processor AttributeError.
        _apply_surya_compat_patches()
        try:
            from surya.foundation import FoundationPredictor
            _rec_model = RecognitionPredictor(FoundationPredictor())
        except (ImportError, TypeError):
            # Older surya without FoundationPredictor
            _rec_model = RecognitionPredictor()

        _det_processor = None
        _rec_processor = None
        _surya_new_api = True
        print("[surya] OCRモデル読み込み完了 (ローカル)", flush=True)
        return
    except ImportError:
        pass
    # surya < 0.6: model/processor API
    try:
        from surya.model.detection.model import (
            load_model as load_det,
            load_processor as load_det_proc,
        )
        from surya.model.recognition.model import load_model as load_rec
        from surya.model.recognition.processor import load_processor as load_rec_proc
        _det_model = load_det()
        _det_processor = load_det_proc()
        _rec_model = load_rec()
        _rec_processor = load_rec_proc()
        _surya_new_api = False
        return
    except ImportError as e:
        raise RuntimeError(f"surya-ocr が必要です: pip install surya-ocr\n{e}") from e


def _ocr_lines(image) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """Run surya OCR; return list of (text, (x1, y1, x2, y2))."""
    _load_models()
    lines: List[Tuple[str, Tuple[int, int, int, int]]] = []

    if _surya_new_api:
        # surya >= 0.6 API:
        #   DetectionPredictor([image])  → TextDetectionResult with .bboxes (PolygonBox list)
        #   RecognitionPredictor([image], langs, bboxes=[[x1,y1,x2,y2],...])
        #       → List[OCRResult], each with .text_lines (TextLine list)

        # Step 1: detect text line bboxes.
        # Pre-processing: upscale small images then pad to square so the internal
        # 512x512 downscale doesn't compress text too aggressively and so aspect
        # ratio is preserved (DetectionPredictor stretches whatever it gets to
        # square).  Padding is centered — the detector is more reliable when
        # content is in the middle of the canvas.
        from PIL import ImageOps as _ImageOps
        orig_w, orig_h = image.size
        long_side = max(orig_w, orig_h)
        scale = max(1.0, 1280.0 / long_side)  # upscale to at least 1280 on long side
        if scale > 1.0:
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            up_image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            up_image = image
            new_w, new_h = orig_w, orig_h

        if new_w != new_h:
            max_dim = max(new_w, new_h)
            det_image = _ImageOps.pad(up_image, (max_dim, max_dim),
                                      color=(255, 255, 255), centering=(0.5, 0.5))
            pad_x = (max_dim - new_w) / 2.0
            pad_y = (max_dim - new_h) / 2.0
        else:
            det_image = up_image
            pad_x = pad_y = 0.0

        det_results = _det_model([det_image], include_maps=True)
        r0 = det_results[0] if det_results else None
        raw_bboxes = getattr(r0, "bboxes", None) or []

        # Diagnostic: print heatmap signal even when no bboxes found.
        hm = getattr(r0, "heatmap", None) if r0 else None
        if hm is not None:
            import numpy as _np
            hm_arr = _np.asarray(hm)
            hm_max = int(hm_arr.max())
            print(f"[surya] detection: {len(raw_bboxes)} bbox(es)"
                  f"  image_size={image.size}"
                  f"  heatmap_max={hm_max}/255", flush=True)
        else:
            print(f"[surya] detection: {len(raw_bboxes)} bbox(es)"
                  f"  image_size={image.size}", flush=True)

        if not raw_bboxes:
            return lines

        # Remap bboxes from padded+upscaled space back to original image coords.
        # surya returns bboxes in the input image's pixel space (max_dim x max_dim),
        # so: subtract padding offset, then divide by upscale factor.
        bbox_coords = []
        for b in raw_bboxes:
            x1, y1, x2, y2 = b.bbox
            x1 = (float(x1) - pad_x) / scale
            y1 = (float(y1) - pad_y) / scale
            x2 = (float(x2) - pad_x) / scale
            y2 = (float(y2) - pad_y) / scale
            x1 = max(0.0, min(x1, orig_w))
            y1 = max(0.0, min(y1, orig_h))
            x2 = max(0.0, min(x2, orig_w))
            y2 = max(0.0, min(y2, orig_h))
            if x2 > x1 and y2 > y1:
                bbox_coords.append([x1, y1, x2, y2])

        if not bbox_coords:
            return lines

        # Step 2: recognise text (pass original image + clipped bboxes)
        # surya >= 0.6 new API: 2nd arg is task_names (not langs); default None →
        # [TaskNames.ocr_with_boxes] per image which is correct when bboxes provided.
        rec_results = _rec_model([image], bboxes=[bbox_coords])

        # Step 3: extract text from OCRResult.text_lines
        if rec_results and getattr(rec_results[0], "text_lines", None):
            for line in rec_results[0].text_lines:
                if line.text.strip():
                    b = line.bbox  # PolygonBox computed property → [x1,y1,x2,y2]
                    lines.append((line.text, (int(b[0]), int(b[1]), int(b[2]), int(b[3]))))

        print(f"[surya] {len(lines)} line(s) extracted:", flush=True)
        for t, bb in lines:
            print(f"  {bb} -> {t!r}", flush=True)
    else:
        from surya.ocr import run_ocr
        results = run_ocr(
            [image], [["ja", "en"]],
            _det_model, _det_processor, _rec_model, _rec_processor,
        )
        if results and results[0].text_lines:
            for line in results[0].text_lines:
                if line.text.strip():
                    b = line.bbox
                    lines.append((line.text, (int(b[0]), int(b[1]), int(b[2]), int(b[3]))))

    return lines


def _get_sensitive_words(text: str) -> List[str]:
    detections = resolve_overlaps(detect_all(text))
    words: List[str] = []
    for det in detections:
        words.extend(det.mask_text.split())
    result = list(set(w for w in words if w.strip()))
    print(f"[surya] sensitive words detected: {result}", flush=True)
    return result


def _find_sensitive_boxes(
    lines: List[Tuple[str, Tuple[int, int, int, int]]],
    sensitive: List[str],
) -> List[Tuple[int, int, int, int]]:
    """Return bboxes of lines that contain any sensitive word."""
    boxes: List[Tuple[int, int, int, int]] = []
    for text, bbox in lines:
        for sw in sensitive:
            if sw in text or text in sw:
                boxes.append(bbox)
                break
    return boxes


def _blackout_regions(image, boxes: List[Tuple[int, int, int, int]]):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for x1, y1, x2, y2 in boxes:
        if x2 > x1 and y2 > y1:
            draw.rectangle([x1, y1, x2, y2], fill="black")
    return image


def process_image(src: Path) -> Path:
    """Run surya OCR and black out sensitive regions."""
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(f"Pillow が必要です: {e}") from e

    img = Image.open(src).convert("RGB")
    lines = _ocr_lines(img)

    if lines:
        full_text = " ".join(t for t, _ in lines)
        sensitive = _get_sensitive_words(full_text)
        if sensitive:
            boxes = _find_sensitive_boxes(lines, sensitive)
            img = _blackout_regions(img, boxes)

    out = make_output_path(src)
    img.save(out)
    return out


def process_image_data(img, mode: str = "blackout") -> "Image":
    """Process a PIL Image object and return masked Image."""
    img = img.convert("RGB")
    lines = _ocr_lines(img)
    if not lines:
        return img

    full_text = " ".join(t for t, _ in lines)
    sensitive = _get_sensitive_words(full_text)
    if not sensitive:
        return img

    boxes = _find_sensitive_boxes(lines, sensitive)
    return _blackout_regions(img, boxes)
