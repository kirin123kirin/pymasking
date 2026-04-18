"""一意性保持方式（不可逆）。
同一テキストが複数箇所に出現する場合、初出順に [カテゴリ][ゼロパディング数字] で統一する。
"""


class UniqueCounter:
    def __init__(self, pad: int = 3) -> None:
        self._pad = pad
        self._counts: dict[str, int] = {}
        self._seen: dict[tuple[str, str], str] = {}

    def encode(self, category: str, text: str) -> str:
        key = (category, text)
        if key not in self._seen:
            count = self._counts.get(category, 0) + 1
            self._counts[category] = count
            self._seen[key] = f"{category}{str(count).zfill(self._pad)}"
        return self._seen[key]
