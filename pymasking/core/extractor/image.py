"""画像ファイルの視覚的マスキング処理（EasyOCR で検出 → 黒塗り）。"""

from pathlib import Path
from typing import List, Tuple

from PIL import Image

from ..detector import detect_all, resolve_overlaps
from . import make_output_path

# モデルの保存先: pymasking/data/model/
_MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "model"

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        _reader = easyocr.Reader(
            ["ja", "en"],
            gpu=False,
            model_storage_directory=str(_MODEL_DIR),
            verbose=False,
        )
    return _reader


def preload_models() -> None:
    """アプリ起動時にバックグラウンドで EasyOCR モデルをロードする。"""
    import logging
    try:
        _get_reader()
    except Exception as e:
        logging.getLogger(__name__).warning("EasyOCR モデルのロードに失敗しました: %s", e)


def _ocr_words(image) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """EasyOCR で画像を解析し (word_text, (x, y, w, h)) のリストを返す。"""
    reader = _get_reader()
    results = reader.readtext(image, detail=1, paragraph=False)

    words: List[Tuple[str, Tuple[int, int, int, int]]] = []
    for bbox, text, _conf in results:
        if not text or not text.strip():
            continue
        # bbox: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - min(xs)), int(max(ys) - min(ys))
        words.append((text, (x, y, w, h)))
    return words


def _get_sensitive_words(text: str) -> List[str]:
    detections = resolve_overlaps(detect_all(text))
    words: List[str] = []
    for det in detections:
        words.extend(det.mask_text.split())
    return list(set(w for w in words if w.strip()))


def _find_sensitive_word_boxes(
    words: List[Tuple[str, Tuple[int, int, int, int]]],
    sensitive: List[str],
) -> List[Tuple[int, int, int, int]]:
    """センシティブ語にマッチする OCR ワードのバウンディングボックスを返す。"""
    boxes: List[Tuple[int, int, int, int]] = []
    for txt, bbox in words:
        for sw in sensitive:
            if sw and (sw in txt or txt in sw):
                boxes.append(bbox)
                break
    return boxes


def _blackout_regions(image, boxes: List[Tuple[int, int, int, int]]):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for x, y, w, h in boxes:
        if w > 0 and h > 0:
            draw.rectangle([x, y, x + w, y + h], fill="black")
    return image


def process_image(src: Path) -> Path:
    """Read image, OCR it, black out sensitive word boxes, and save a copy."""
    img = Image.open(src).convert("RGB")
    words = _ocr_words(img)

    if words:
        full_text = " ".join(t for t, _ in words)
        sensitive = _get_sensitive_words(full_text)
        if sensitive:
            boxes = _find_sensitive_word_boxes(words, sensitive)
            img = _blackout_regions(img, boxes)

    out = make_output_path(src)
    img.save(out)
    return out


def process_image_data(img, mode: str = "blackout") -> "Image":
    """Process a PIL Image object and return the masked Image."""
    img = img.convert("RGB")
    words = _ocr_words(img)
    if not words:
        return img

    full_text = " ".join(t for t, _ in words)
    sensitive = _get_sensitive_words(full_text)
    if not sensitive:
        return img

    boxes = _find_sensitive_word_boxes(words, sensitive)
    return _blackout_regions(img, boxes)
