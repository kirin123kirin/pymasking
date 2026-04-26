"""ピッグペン暗号（暗号化のみ）。
マルチバイト文字列は UTF-8 hex に変換後、16文字（0-9,A-F）を
数学記号ブロックの固有 Unicode 文字へ置換する。
"""

# hex 文字 → 数学記号（U+229E〜U+22AD）の全単射マッピング
_ENC: dict[str, str] = {
    "0": "⊞", "1": "⊟", "2": "⊠", "3": "⊡",
    "4": "⊢", "5": "⊣", "6": "⊤", "7": "⊥",
    "8": "⊦", "9": "⊧", "A": "⊨", "B": "⊩",
    "C": "⊪", "D": "⊫", "E": "⊬", "F": "⊭",
}


def encrypt(text: str) -> str:
    hex_str = text.encode("utf-8").hex().upper()
    return "".join(_ENC[c] for c in hex_str)
