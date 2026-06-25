_MISSING = object()


def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for key, value in b.items():
            existing = a.get(key, _MISSING)
            out[key] = merge(existing, value) if existing is not _MISSING else value
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return b
