def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for key, value in b.items():
            out[key] = merge(a[key], value) if key in a else value
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return b
