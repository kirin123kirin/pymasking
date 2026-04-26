"""テキストのマスキング処理本体。"""

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
