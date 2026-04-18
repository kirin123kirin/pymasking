"""伏字方式（不可逆）。文字数分の ● で置換する。"""


def encode(text: str) -> str:
    return "●" * len(text)
