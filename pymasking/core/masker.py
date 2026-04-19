"""テキストのマスキング処理本体。"""

import re
from typing import Literal

from .detector import detect_all, resolve_overlaps
from .cipher import pigpen, blackout
from .cipher.unique import UniqueCounter

MaskMode = Literal["blackout", "unique", "pigpen"]


def mask_text(text: str, mode: MaskMode = "blackout", categories: set = None) -> str:
    """テキスト中のセンシティブ情報をマスキングして返す。"""
    detections = resolve_overlaps(detect_all(text, categories=categories))
    if not detections:
        return text

    counter = UniqueCounter() if mode == "unique" else None
    chars = list(text)

    # 後ろから置換することで文字位置のずれを防ぐ
    for det in reversed(detections):
        mt = det.mask_text
        if not mt:
            continue

        if mode == "blackout":
            replacement = blackout.encode(mt)
        elif mode == "unique":
            replacement = counter.encode(det.category, mt)  # type: ignore[union-attr]
        else:
            replacement = f"【{det.category}:{pigpen.encrypt(mt)}:】"

        chars[det.mask_start:det.mask_end] = list(replacement)

    return "".join(chars)


def unmask_text(text: str) -> str:
    """ピッグペン暗号化されたテキストを復号して返す。"""
    pattern = r"【([^:]+):([^:]+):】"

    def _replace(m: re.Match) -> str:
        try:
            return pigpen.decrypt(m.group(2))
        except ValueError:
            return m.group(0)

    return re.sub(pattern, _replace, text)
