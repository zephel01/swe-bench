"""Deserialize a line produced by :func:`encode.dumps` back to a record."""


def _split_fields(line):
    """Split ``line`` on unescaped pipes, unescaping backslash sequences."""
    fields = []
    buf = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            buf.append(line[i + 1])
            i += 2
            continue
        if ch == "|":
            fields.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    fields.append("".join(buf))
    return fields


def loads(line):
    """Parse ``line`` back into a record dict."""
    if line == "":
        return {}
    result = {}
    for field in _split_fields(line):
        key, rest = field.split("=", 1)
        tag, value = rest.split(":", 1)
        if tag == "s":
            result[key] = value
        elif tag == "i":
            result[key] = int(value)
        elif tag == "b":
            result[key] = bool(value)
        elif tag == "n":
            result[key] = None
    return result
