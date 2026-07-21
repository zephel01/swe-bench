"""Templated email body renderer with HTML-escaped substitutions."""
from __future__ import annotations

import html
import re

_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, ctx: dict[str, str]) -> str:
    """Return ``template`` with ``{{ name }}`` placeholders substituted."""
    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = ctx.get(key, "")
        return str(value)

    return html.escape(_VAR.sub(_repl, template), quote=True)
