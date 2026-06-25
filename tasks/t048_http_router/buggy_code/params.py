def convert(typ, raw):
    if typ in ("", "str"):
        return raw
    if typ == "int":
        return int(raw)
    raise ValueError(f"unknown param type: {typ}")
