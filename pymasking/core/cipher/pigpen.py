"""ピッグペン暗号（可逆）。
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
_DEC: dict[str, str] = {v: k for k, v in _ENC.items()}


def encrypt(text: str) -> str:
    hex_str = text.encode("utf-8").hex().upper()
    return "".join(_ENC[c] for c in hex_str)


def decrypt(encoded: str) -> str:
    try:
        hex_str = "".join(_DEC[c] for c in encoded)
        return bytes.fromhex(hex_str).decode("utf-8")
    except (KeyError, ValueError) as exc:
        raise ValueError(f"ピッグペン復号失敗: {exc}") from exc
