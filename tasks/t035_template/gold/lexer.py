"""最小テンプレートの字句解析。{{ var }} と {% for x in items %}/{% endfor %}."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\{\{(.*?)\}\}|\{%(.*?)%\}", re.S)


def tokenize(src: str) -> list[tuple]:
    tokens: list[tuple] = []
    pos = 0
    for m in _TOKEN.finditer(src):
        if m.start() > pos:
            tokens.append(("text", src[pos:m.start()]))
        if m.group(1) is not None:
            tokens.append(("var", m.group(1).strip()))
        else:
            tag = m.group(2).strip().split()
            if tag and tag[0] == "for":
                # for x in items
                tokens.append(("for", tag[1], tag[3]))
            elif tag and tag[0] == "endfor":
                tokens.append(("endfor",))
            else:
                raise ValueError(f"unknown tag: {m.group(2)!r}")
        pos = m.end()
    if pos < len(src):
        tokens.append(("text", src[pos:]))
    return tokens
