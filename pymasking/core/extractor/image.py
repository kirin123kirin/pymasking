"""画像ファイルの視覚的マスキング処理（surya-ocr で検出 → 黒塗り）。"""

import os
from pathlib import Path
from typing import List, Tuple

from ..detector import detect_all, resolve_overlaps
from . import make_output_path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_HF_CACHE = _REPO_ROOT / "data" / "models" / "hf_cache"

_det_model = None
_det_processor = None
_rec_model = None
_rec_processor = None


def _ensure_hf_home() -> None:
    _HF_CACHE.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MODEL_CACHE_DIR", str(_HF_CACHE))


def _load_models() -> None:
    global _det_model, _det_processor, _rec_model, _rec_processor
    if _det_model is not None:
        return
    _ensure_hf_home()
    try:
        from surya.model.detection.model import (
            load_model as load_det,
            load_processor as load_det_proc,
        )
        from surya.model.recognition.model import load_model as load_rec
        from surya.model.recognition.processor import load_processor as load_rec_proc
    except ImportError as e:
        raise RuntimeError(f"surya-ocr が必要です: pip install surya-ocr\n{e}") from e
    _det_model = load_det()
    _det_processor = load_det_proc()
    _rec_model = load_rec()
    _rec_processor = load_rec_proc()


def _ocr_lines(image) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """Run surya OCR; return list of (text, (x1, y1, x2, y2))."""
    _load_models()
    from surya.ocr import run_ocr

    results = run_ocr(
        [image],
        [["ja", "en"]],
        _det_model,
        _det_processor,
        _rec_model,
        _rec_processor,
    )
    lines: List[Tuple[str, Tuple[int, int, int, int]]] = []
    if results and results[0].text_lines:
        for line in results[0].text_lines:
            if line.text.strip():
                b = line.bbox  # [x1, y1, x2, y2]
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
