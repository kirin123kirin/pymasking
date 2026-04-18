"""プレーンテキストファイルのマスキング処理。"""

from pathlib import Path

from ..masker import mask_text, MaskMode
from . import make_output_path


def _detect_encoding(path: Path) -> str:
    try:
        import chardet
        raw = path.read_bytes()
        result = chardet.detect(raw)
        return result.get("encoding") or "utf-8"
    except ImportError:
        return "utf-8"


def process_text(path: Path, mode: MaskMode = "blackout") -> Path:
    encoding = _detect_encoding(path)
    text = path.read_text(encoding=encoding, errors="replace")
    masked = mask_text(text, mode)
    out = make_output_path(path)
    out.write_text(masked, encoding="utf-8")
    return out
