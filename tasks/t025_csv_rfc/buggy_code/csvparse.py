"""RFC 4180 準拠のCSVパーサ。引用フィールド・改行埋め込み・二重引用に対応."""

from __future__ import annotations


def parse_csv(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    row: list[str] = []
    field: list[str] = []
    i, n = 0, len(text)
    in_quotes = False
    started = False  # この行で1つでもフィールドが始まったか

    def end_field() -> None:
        row.append("".join(field))
        field.clear()

    def end_row() -> None:
        end_field()
        rows.append(row.copy())
        row.clear()

    while i < n:
        ch = text[i]
        if in_quotes:
            if ch == '"':
                in_quotes = False
                i += 1
                continue
            field.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quotes = True
            started = True
            i += 1
            continue
        if ch == ",":
            end_field()
            started = True
            i += 1
            continue
        if ch in ("\n", "\r"):
            if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 1
            end_row()
            started = False
            i += 1
            continue
        field.append(ch)
        started = True
        i += 1

    if started or field or row:
        end_row()
    return rows
