# Every character that any parser might treat as the end of a line makes the
# value unsafe. This is the full set that str.splitlines() recognises, which is
# wider than just CR/LF: it also includes VT, FF, the information separators
# and the Unicode line breaks NEL (U+0085), LS (U+2028) and PS (U+2029).
_LINE_BREAKS = (
    "\n", "\r", "\v", "\f",
    "\x1c", "\x1d", "\x1e", "\x85", " ", " ",
)


def sanitize_header_value(value):
    for ch in value:
        if ch in _LINE_BREAKS:
            raise ValueError("header value contains a line break")
        if ch == "\t":
            continue
        if ord(ch) < 0x20 or ord(ch) == 0x7F:
            raise ValueError("header value contains a control character")
    return value
