def merge(a, b):
    out = dict(a)
    for key, value in b.items():
        if key in a and isinstance(a[key], dict):
            out[key] = merge(a[key], value)
        elif value is not None:
            out[key] = value
    return out
