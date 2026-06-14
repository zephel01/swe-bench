"""変数つき式評価器。** は右結合・優先順位は単項マイナスより高い."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\*\*|\d+\.?\d*|[A-Za-z_]\w*|[-+*/()]")
_WS = re.compile(r"\s*")
_NUM = re.compile(r"\d+\.?\d*")
_NAME = re.compile(r"[A-Za-z_]\w*")


def _tokenize(s: str) -> list[str]:
    pos = 0
    out: list[str] = []
    while pos < len(s):
        pos = _WS.match(s, pos).end()
        if pos >= len(s):
            break
        m = _TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"bad token at {pos}: {s[pos]!r}")
        out.append(m.group(0))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, toks: list[str], env: dict) -> None:
        self.t = toks
        self.i = 0
        self.env = env

    def _peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def _eat(self) -> str:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        value = self._expr()
        if self.i != len(self.t):
            raise ValueError("trailing tokens")
        return value

    def _expr(self):
        value = self._mul()
        while self._peek() in ("+", "-"):
            op = self._eat()
            rhs = self._mul()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _mul(self):
        value = self._unary()
        while self._peek() in ("*", "/"):
            op = self._eat()
            rhs = self._unary()
            value = value * rhs if op == "*" else value / rhs
        return value

    def _unary(self):
        if self._peek() == "-":
            self._eat()
            return -self._unary()
        return self._power()

    def _power(self):
        base = self._atom()
        if self._peek() == "**":
            self._eat()
            return base ** self._unary()  # 右結合
        return base

    def _atom(self):
        tok = self._peek()
        if tok is None:
            raise ValueError("unexpected end of input")
        if tok == "(":
            self._eat()
            value = self._expr()
            if self._peek() != ")":
                raise ValueError("missing closing parenthesis")
            self._eat()
            return value
        self._eat()
        if _NUM.fullmatch(tok):
            return float(tok) if "." in tok else int(tok)
        if _NAME.fullmatch(tok):
            if tok not in self.env:
                raise ValueError(f"unknown variable: {tok}")
            return self.env[tok]
        raise ValueError(f"unexpected token: {tok!r}")


def evaluate(expression: str, env: dict | None = None):
    return _Parser(_tokenize(expression), env or {}).parse()
