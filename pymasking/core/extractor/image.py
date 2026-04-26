"""画像ファイルの視覚的マスキング処理（Tesseract OCR で検出 → 黒塗り）。"""

import os
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from ..detector import detect_all, resolve_overlaps
from . import make_output_path

_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

_tesseract_configured = False


def _configure_tesseract() -> None:
    """Locate tesseract.exe and tessdata/; raise a user-friendly error if missing."""
    global _tesseract_configured
    if _tesseract_configured:
        return
    import shutil
    import pytesseract

    if shutil.which("tesseract"):
        _tesseract_configured = True
        return

    username = os.environ.get("USERNAME", "")
    candidates = _TESSERACT_CANDIDATES + [
        rf"C:\Users\{username}\AppData\Local\Tesseract-OCR\tesseract.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            pytesseract.pytesseract.tesseract_cmd = str(p)
            tessdata = Path(p).parent / "tessdata"
            if tessdata.exists():
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            _tesseract_configured = True
            return

    raise RuntimeError(
        "Tesseract-OCR が見つかりません。\n"
        "https://github.com/UB-Mannheim/tesseract/wiki からインストーラーをダウンロードし、\n"
        "「Additional language data」で「Japanese (jpn)」を選択してインストールしてください。\n"
        "インストール後、Tesseract のフォルダ（例: C:\\Program Files\\Tesseract-OCR）を PATH に追加してください。"
    )


def preload_models() -> None:
    """Lightweight no-op kept for app-startup compatibility (Tesseract loads per-call)."""
    import logging
    try:
        _configure_tesseract()
    except Exception as e:
        logging.getLogger(__name__).warning("Tesseract の初期化に失敗しました: %s", e)


def _ocr_words(image) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """Run Tesseract OCR on image; return list of (word_text, (x, y, w, h))."""
    import pytesseract

    _configure_tesseract()
    data = pytesseract.image_to_data(
        image, lang="jpn+eng", output_type=pytesseract.Output.DICT
    )

    words: List[Tuple[str, Tuple[int, int, int, int]]] = []
    for i, txt in enumerate(data["text"]):
        if not txt or not txt.strip():
            continue
        words.append((
            txt,
            (int(data["left"][i]), int(data["top"][i]),
             int(data["width"][i]), int(data["height"][i])),
        ))
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
    """Return (x, y, w, h) boxes of OCR words that match any sensitive term."""
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
