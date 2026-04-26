"""PDF の視覚的マスキング処理（PyMuPDF でテキスト検索 → 黒塗り）。"""

from pathlib import Path

from ..detector import detect_all, resolve_overlaps
from . import make_output_path


def process_pdf(src: Path) -> Path:
    """センシティブテキストを検出し、PDF 上で黒矩形により視覚的に塗りつぶす。"""
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError(f"PyMuPDF が必要です: pip install PyMuPDF  ({e})") from e

    doc = fitz.open(str(src))

    for page in doc:
        # ページ全体のテキストを取得して検出
        full_text = page.get_text("text")
        detections = resolve_overlaps(detect_all(full_text))

        for det in detections:
            target = det.mask_text.strip()
            if not target:
                continue
            rects = page.search_for(target)
            for rect in rects:
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))

    out = make_output_path(src)
    doc.save(str(out))
    doc.close()
    return out
