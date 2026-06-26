def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for key, value in b.items():
            if key in a:
                out[key] = merge(a[key], value)
            else:
                out[key] = value
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return b
