"""JSONサブセットの再帰下降パーサ (エスケープ・数値・入れ子対応)."""

from __future__ import annotations

import re

_NUM = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_SIMPLE = {
    '"': '"', "\\": "\\", "/": "/",
    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
}


class _Parser:
    def __init__(self, text: str) -> None:
        self.s = text
        self.i = 0

    def parse(self):
        self._ws()
        value = self._value()
        self._ws()
        if self.i != len(self.s):
            raise ValueError("trailing data")
        return value

    def _peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def _ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def _value(self):
        ch = self._peek()
        if ch == "{":
            return self._obj()
        if ch == "[":
            return self._arr()
        if ch == '"':
            return self._str()
        if ch == "-" or ch.isdigit():
            return self._num()
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(lit, self.i):
                self.i += len(lit)
                return val
        raise ValueError(f"unexpected character: {ch!r}")

    def _num(self):
        m = _NUM.match(self.s, self.i)
        if not m:
            raise ValueError("invalid number")
        text = m.group(0)
        self.i = m.end()
        if any(c in text for c in ".eE"):
            return float(text)
        return int(text)

    def _str(self) -> str:
        self.i += 1
        out: list[str] = []
        while self.i < len(self.s):
            ch = self.s[self.i]
            if ch == '"':
                self.i += 1
                return "".join(out)
            if ch == "\\":
                self.i += 1
                esc = self.s[self.i]
                if esc in _SIMPLE:
                    out.append(_SIMPLE[esc])
                    self.i += 1
                else:
                    out.append(esc)
                    self.i += 1
                continue
            out.append(ch)
            self.i += 1
        raise ValueError("unterminated string")

    def _arr(self) -> list:
        self.i += 1
        arr: list = []
        self._ws()
        if self._peek() == "]":
            self.i += 1
            return arr
        while True:
            self._ws()
            arr.append(self._value())
            self._ws()
            c = self._peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise ValueError("expected ',' or ']'")

    def _obj(self) -> dict:
        self.i += 1
        obj: dict = {}
        self._ws()
        if self._peek() == "}":
            self.i += 1
            return obj
        while True:
            self._ws()
            if self._peek() != '"':
                raise ValueError("expected string key")
            key = self._str()
            self._ws()
            if self._peek() != ":":
                raise ValueError("expected ':'")
            self.i += 1
            self._ws()
            obj[key] = self._value()
            self._ws()
            c = self._peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise ValueError("expected ',' or '}'")


def loads(text: str):
    return _Parser(text).parse()
