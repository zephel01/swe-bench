def merge(a, b):
    for key, value in b.items():
        if key in a and isinstance(a[key], dict) and isinstance(value, dict):
            merge(a[key], value)
        else:
            a[key] = value
    return a
