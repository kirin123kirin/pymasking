"""ファイル種別に応じた処理を振り分ける。"""

from pathlib import Path
from typing import Union

_PLAINTEXT_EXTS = {
    ".txt", ".csv", ".tsv", ".json", ".xml", ".html", ".htm",
    ".md", ".rst", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".log", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".h", ".cs", ".sql", ".sh", ".bat", ".cmd", ".ps1",
}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

_UNMASK_EXTS = {
    ".txt", ".csv", ".tsv", ".json", ".xml", ".html", ".htm",
    ".md", ".rst", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".log",
    ".docx", ".xlsx", ".pptx",
}


def process_file(file_path: Union[str, Path], mode: str = "blackout") -> Path:
    """ファイルをマスキング処理し、出力ファイルパスを返す。"""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".docx", ".xlsx", ".pptx"):
        from .office import process_office
        return process_office(path, mode)
    elif ext in _IMAGE_EXTS:
        from .image import process_image
        return process_image(path)
    elif ext == ".pdf":
        from .pdf_handler import process_pdf
        return process_pdf(path)
    else:
        from .plaintext import process_text
        return process_text(path, mode)


def unmask_file(file_path: Union[str, Path]) -> Path:
    """pigpen 暗号化されたファイルを復号し、出力ファイルパスを返す。"""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".pdf"):
        raise ValueError("暗号化解除は画像・PDF には対応していません（視覚的塗りつぶしのため）")

    if ext in (".docx", ".xlsx", ".pptx"):
        from .office import unmask_office
        return unmask_office(path)

    # プレーンテキスト系
    from ..masker import unmask_text
    try:
        import chardet
        raw = path.read_bytes()
        enc = chardet.detect(raw).get("encoding") or "utf-8"
    except ImportError:
        enc = "utf-8"
        raw = path.read_bytes()
    text = raw.decode(enc, errors="replace")
    restored = unmask_text(text)
    out = path.parent / f"{path.stem}_unmasked{path.suffix}"
    out.write_text(restored, encoding="utf-8")
    return out


def make_output_path(path: Path) -> Path:
    """入力パスに _masked サフィックスを付けた出力パスを返す。"""
    return path.parent / f"{path.stem}_masked{path.suffix}"
