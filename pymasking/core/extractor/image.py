"""画像ファイルの視覚的マスキング処理（surya-ocr で検出 → 黒塗り）。"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

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


def _load_models() -> None:
    global _det_model, _det_processor, _rec_model, _rec_processor, _surya_new_api
    if _det_model is not None and _surya_new_api is not None:
        return
    _ensure_hf_home()
    # surya >= 0.6: predictor-based API
    try:
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor
        import inspect
        _det_model = DetectionPredictor()
        # Patch attributes missing from older model checkpoints (surya/issues/492)
        if hasattr(_det_model, 'model') and hasattr(_det_model.model, 'config'):
            cfg = _det_model.model.config
            if not hasattr(cfg, 'bbox_size'):
                cfg.bbox_size = 4
        if not hasattr(_det_model, 'tasks'):
            _det_model.tasks = []
        rec_params = inspect.signature(RecognitionPredictor.__init__).parameters
        if "foundation_predictor" in rec_params:
            _rec_model = RecognitionPredictor(_det_model)
        else:
            _rec_model = RecognitionPredictor()
        _det_processor = None
        _rec_processor = None
        _surya_new_api = True
        _log.info("[surya] new API loaded (det=%s, rec=%s)", type(_det_model).__name__, type(_rec_model).__name__)
        print(f"[surya] new API loaded det={type(_det_model).__name__} rec={type(_rec_model).__name__}", flush=True)
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
        # surya >= 0.6: separate detection → crop → recognition pipeline.
        # RecognitionPredictor takes individual text-line crops, NOT full-page images.

        # Step 1: detect text line bboxes
        det_results = _det_model([image])

        # Diagnose result structure and heatmap values
        if det_results:
            r0 = det_results[0]
            # Heatmap stats — tells us if the model is actually running inference
            for hm_attr in ("heatmap", "affinity_map"):
                hm = getattr(r0, hm_attr, None)
                if hm is not None:
                    try:
                        import numpy as np
                        arr = np.array(hm)
                        print(f"[surya] {hm_attr}: shape={arr.shape} min={arr.min():.4f} max={arr.max():.4f} mean={arr.mean():.4f}", flush=True)
                    except Exception as e:
                        print(f"[surya] {hm_attr}: type={type(hm).__name__} (stats error: {e})", flush=True)
        else:
            print("[surya] det_results is empty/None", flush=True)
            return lines

        n_bboxes = len(det_results[0].bboxes) if getattr(det_results[0], "bboxes", None) else 0
        print(f"[surya] detection: {n_bboxes} bbox(es) found  image_size={image.size}", flush=True)

        if not n_bboxes:
            return lines

        # Step 2: crop each detected region
        crops: List = []
        coords: List[Tuple[int, int, int, int]] = []
        for bbox_obj in det_results[0].bboxes:
            b = bbox_obj.bbox  # [x1, y1, x2, y2]
            try:
                x1, y1, x2, y2 = int(b[0]), int(b[1]), int(b[2]), int(b[3])
            except (TypeError, ValueError) as e:
                _log.warning("[surya] bad bbox %r: %s", b, e)
                print(f"[surya] bad bbox {b!r}: {e}", flush=True)
                continue
            if x2 > x1 and y2 > y1:
                crops.append(image.crop((x1, y1, x2, y2)))
                coords.append((x1, y1, x2, y2))

        _log.info("[surya] %d valid crop(s)", len(crops))
        print(f"[surya] {len(crops)} valid crop(s)", flush=True)
        if not crops:
            return lines

        # Step 3: recognise text in each crop (one lang list per crop)
        rec_results = _rec_model(crops, [["ja", "en"]] * len(crops))

        # Log first result structure to help diagnose API shape
        if rec_results:
            r0 = rec_results[0]
            attrs = [a for a in dir(r0) if not a.startswith("_")]
            _log.info("[surya] rec result[0] type=%s attrs=%s", type(r0).__name__, attrs)
            print(f"[surya] rec result[0] type={type(r0).__name__} attrs={attrs}", flush=True)

        # Step 4: pair text with original bbox coordinates
        for bbox, rec in zip(coords, rec_results):
            text = ""
            if hasattr(rec, "text"):
                text = rec.text or ""
            elif hasattr(rec, "text_lines") and rec.text_lines:
                text = " ".join(tl.text for tl in rec.text_lines if tl.text)
            # last resort: try string conversion
            if not text and hasattr(rec, "__str__"):
                candidate = str(rec).strip()
                if len(candidate) < 500:  # sanity check
                    text = candidate
            if text.strip():
                lines.append((text, bbox))

        _log.info("[surya] %d line(s) extracted", len(lines))
        print(f"[surya] {len(lines)} line(s) extracted", flush=True)
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
    return list(set(w for w in words if w.strip()))


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
