"""画像ファイルの視覚的マスキング処理（OCR で検出 → 黒塗り）。"""

from pathlib import Path
from typing import List, Tuple

from ..detector import detect_all, resolve_overlaps
from . import make_output_path


def _get_sensitive_words(text: str) -> List[str]:
    detections = resolve_overlaps(detect_all(text))
    words = []
    for det in detections:
        words.extend(det.mask_text.split())
    return list(set(w for w in words if w.strip()))


def _blackout_regions(image, boxes: List[Tuple[int, int, int, int]]):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for x, y, w, h in boxes:
        if w > 0 and h > 0:
            draw.rectangle([x, y, x + w, y + h], fill="black")
    return image


def process_image(src: Path) -> Path:
    """OCR でテキストを検出し、センシティブ領域を黒塗りする。"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(f"pytesseract または Pillow が必要です: {e}") from e

    img = Image.open(src).convert("RGB")

    data = pytesseract.image_to_data(
        img, lang="jpn+eng", output_type=pytesseract.Output.DICT
    )

    words = data["text"]
    full_text = " ".join(w for w in words if w.strip())
    sensitive = _get_sensitive_words(full_text)

    if not sensitive:
        out = make_output_path(src)
        img.save(out)
        return out

    boxes: List[Tuple[int, int, int, int]] = []
    for i, word in enumerate(words):
        if not word.strip():
            continue
        for sw in sensitive:
            if word in sw or sw in word:
                boxes.append((
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                ))
                break

    img = _blackout_regions(img, boxes)
    out = make_output_path(src)
    img.save(out)
    return out


def process_image_data(img, mode: str = "blackout") -> "Image":
    """PIL Image オブジェクトを受け取って黒塗り処理した Image を返す。"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(f"pytesseract または Pillow が必要です: {e}") from e

    img = img.convert("RGB")
    data = pytesseract.image_to_data(
        img, lang="jpn+eng", output_type=pytesseract.Output.DICT
    )
    words = data["text"]
    full_text = " ".join(w for w in words if w.strip())
    sensitive = _get_sensitive_words(full_text)

    if not sensitive:
        return img

    boxes = []
    for i, word in enumerate(words):
        if not word.strip():
            continue
        for sw in sensitive:
            if word in sw or sw in word:
                boxes.append((
                    data["left"][i], data["top"][i],
                    data["width"][i], data["height"][i],
                ))
                break

    return _blackout_regions(img, boxes)
