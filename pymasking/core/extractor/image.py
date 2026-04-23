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

        _det_model = DetectionPredictor()
        # Patch attributes missing from older model checkpoints (surya/issues/492)
        if hasattr(_det_model, 'model') and hasattr(_det_model.model, 'config'):
            cfg = _det_model.model.config
            if not hasattr(cfg, 'bbox_size'):
                cfg.bbox_size = 4

        # RecognitionPredictor requires FoundationPredictor (not DetectionPredictor).
        # Passing DetectionPredictor caused processor.image_processor AttributeError.
        # Monkey-patch: checkpoint config JSON omits pad_token_id; newer transformers
        # raises AttributeError instead of returning None (surya/issues/pad_token_id).
        try:
            from surya.common.surya.decoder import SuryaDecoderConfig
            if not hasattr(SuryaDecoderConfig, 'pad_token_id'):
                SuryaDecoderConfig.pad_token_id = 0
        except Exception:
            pass
        try:
            from surya.foundation import FoundationPredictor
            _rec_model = RecognitionPredictor(FoundationPredictor())
        except (ImportError, TypeError):
            # Older surya without FoundationPredictor
            _rec_model = RecognitionPredictor()

        _det_processor = None
        _rec_processor = None
        _surya_new_api = True
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
        # surya >= 0.6 API:
        #   DetectionPredictor([image])  → TextDetectionResult with .bboxes (PolygonBox list)
        #   RecognitionPredictor([image], langs, bboxes=[[x1,y1,x2,y2],...])
        #       → List[OCRResult], each with .text_lines (TextLine list)

        # Step 1: detect text line bboxes
        det_results = _det_model([image])
        if not det_results or not getattr(det_results[0], "bboxes", None):
            print(f"[surya] detection: 0 bboxes  image_size={image.size}", flush=True)
            return lines

        raw_bboxes = det_results[0].bboxes
        n_bboxes = len(raw_bboxes)
        print(f"[surya] detection: {n_bboxes} bbox(es)  image_size={image.size}", flush=True)

        # Step 2: recognise text (pass full image + pre-computed bboxes)
        # bboxes format: List[List[List[int]]] — one list of boxes per image
        bbox_coords = [list(b.bbox) for b in raw_bboxes]  # [[x1,y1,x2,y2], ...]
        rec_results = _rec_model([image], [["ja", "en"]], bboxes=[bbox_coords])

        # Step 3: extract text from OCRResult.text_lines
        if rec_results and getattr(rec_results[0], "text_lines", None):
            for line in rec_results[0].text_lines:
                if line.text.strip():
                    b = line.bbox  # PolygonBox computed property → [x1,y1,x2,y2]
                    lines.append((line.text, (int(b[0]), int(b[1]), int(b[2]), int(b[3]))))

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
