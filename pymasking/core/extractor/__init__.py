"""ファイル種別に応じた処理を振り分ける。"""

from pathlib import Path
from typing import Union

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def process_file(file_path: Union[str, Path], mode: str = "blackout", categories=None, options=None) -> Path:
    """ファイルをマスキング処理し、出力ファイルパスを返す。"""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".docx", ".xlsx", ".pptx"):
        from .office import process_office
        return process_office(path, mode, categories=categories, options=options)
    elif ext in _IMAGE_EXTS:
        from .image import process_image
        return process_image(path)
    elif ext == ".pdf":
        from .pdf_handler import process_pdf
        return process_pdf(path)
    else:
        from .plaintext import process_text
        return process_text(path, mode, categories=categories)



def make_output_path(path: Path) -> Path:
    """入力パスに _masked サフィックスを付けた出力パスを返す。"""
    return path.parent / f"{path.stem}_変換後{path.suffix}"
