"""テンプレート描画。変数出力はHTMLエスケープする (autoescape)."""

from __future__ import annotations

from lexer import tokenize

_ESCAPE = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def escape(text: str) -> str:
    return "".join(_ESCAPE.get(c, c) for c in text)


def _render(tokens: list[tuple], i: int, ctx: dict, out: list[str]) -> int:
    while i < len(tokens):
        tok = tokens[i]
        kind = tok[0]
        if kind == "text":
            out.append(tok[1])
            i += 1
        elif kind == "var":
            out.append(str(ctx[tok[1]]))
            i += 1
        elif kind == "for":
            _, var, iterable = tok
            body_start = i + 1
            i = body_start
            for item in ctx[iterable]:
                ctx[var] = item
                i = _render(tokens, body_start, ctx, out)
            if i >= len(tokens) or tokens[i][0] != "endfor":
                raise ValueError("missing endfor")
            i += 1
        elif kind == "endfor":
            return i
        else:
            raise ValueError(f"bad token: {tok!r}")
    return i


def render(src: str, ctx: dict) -> str:
    out: list[str] = []
    _render(tokenize(src), 0, ctx or {}, out)
    return "".join(out)
