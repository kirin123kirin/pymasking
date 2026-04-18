"""ファイル種別に応じた処理を振り分ける。"""

from pathlib import Path
from typing import Union

_PLAINTEXT_EXTS = {
    ".txt", ".csv", ".tsv", ".json", ".xml", ".html", ".htm",
    ".md", ".rst", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".log", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".h", ".cs", ".sql", ".sh", ".bat", ".cmd", ".ps1",
}


def process_file(file_path: Union[str, Path], mode: str = "blackout") -> Path:
    """ファイルをマスキング処理し、出力ファイルパスを返す。"""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".docx", ".xlsx", ".pptx"):
        from .office import process_office
        return process_office(path, mode)
    elif ext in (".jpg", ".jpeg", ".png"):
        from .image import process_image
        return process_image(path)
    elif ext == ".pdf":
        from .pdf_handler import process_pdf
        return process_pdf(path)
    else:
        from .plaintext import process_text
        return process_text(path, mode)


def make_output_path(path: Path) -> Path:
    """入力パスに _masked サフィックスを付けた出力パスを返す。"""
    return path.parent / f"{path.stem}_masked{path.suffix}"
