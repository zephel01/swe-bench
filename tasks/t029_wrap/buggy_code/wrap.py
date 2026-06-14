"""表示幅 (全角=2) を考慮した単語折返し."""

from __future__ import annotations

import unicodedata


def char_width(ch: str) -> int:
    return 1


def text_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def wrap(text: str, max_width: int) -> list[str]:
    if max_width <= 0:
        raise ValueError("max_width must be positive")
    lines: list[str] = []
    cur: list[str] = []
    cur_w = 0
    for word in text.split():
        ww = text_width(word)
        if cur and cur_w + 1 + ww > max_width:
            lines.append(" ".join(cur))
            cur, cur_w = [word], ww
        elif cur:
            cur.append(word)
            cur_w += 1 + ww
        else:
            cur, cur_w = [word], ww
    if cur:
        lines.append(" ".join(cur))
    return lines
