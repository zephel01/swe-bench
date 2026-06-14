"""インライン要素: HTMLエスケープ・**強調**・`コード`."""

from __future__ import annotations

import re

_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def escape(text: str) -> str:
    return "".join(_ESC.get(c, c) for c in text)


def render_inline(text: str) -> str:
    out = escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return out
