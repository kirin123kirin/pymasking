"""クリップボードからのデータ取得（Windows 11 対応）。"""

import sys
import tempfile
from pathlib import Path
from typing import Tuple, Union


def get_clipboard() -> Tuple[str, Union[str, "Image", Path, None]]:
    """クリップボードを読み取り (type, content) を返す。

    type: 'text' | 'image' | 'file' | 'unknown'
    """
    # Windows: PIL ImageGrab でまず画像・ファイルリストを試みる
    if sys.platform == "win32":
        try:
            from PIL import ImageGrab
            data = ImageGrab.grabclipboard()
            if data is not None:
                if isinstance(data, list) and data:
                    return "file", Path(data[0])
                return "image", data
        except Exception:
            pass

        # win32clipboard でファイルパス・テキストを取得
        try:
            import win32clipboard
            import win32con
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    if files:
                        return "file", Path(files[0])
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    if text:
                        return "text", text
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass

    # 汎用フォールバック（テキストのみ）
    try:
        import pyperclip
        text = pyperclip.paste()
        if text:
            return "text", text
    except Exception:
        pass

    return "unknown", None


def open_with_default_app(path: Path) -> None:
    """既定のアプリでファイルを開く（Windows）。"""
    import os
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", str(path)])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", str(path)])


def save_to_temp(content: str, suffix: str = ".txt") -> Path:
    """テキストを一時ファイルに保存してパスを返す。"""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=suffix, delete=False, prefix="pymasking_"
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


def save_image_to_temp(img, suffix: str = ".png") -> Path:
    """PIL Image を一時ファイルに保存してパスを返す。"""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix="pymasking_")
    tmp.close()
    img.save(tmp.name)
    return Path(tmp.name)
