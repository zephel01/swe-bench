"""ブロック要素: 見出し・段落・箇条書きリスト (連続する - をまとめる)."""

from __future__ import annotations

from inline import render_inline


def render(md: str) -> str:
    lines = md.split("\n")
    html: list[str] = []
    items: list[str] = []

    def flush_list() -> None:
        if items:
            inner = "".join(f"<li>{render_inline(x)}</li>" for x in items)
            html.append(f"<ul>{inner}</ul>")
            items.clear()

    for line in lines:
        if line.startswith("- "):
            items.append(line[2:])
            continue
        flush_list()
        if not line.strip():
            continue
        if line.startswith("# "):
            html.append(f"<h1>{render_inline(line[2:])}</h1>")
        else:
            html.append(f"<p>{render_inline(line)}</p>")
    flush_list()
    return "".join(html)
