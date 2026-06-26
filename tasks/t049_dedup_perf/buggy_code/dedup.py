def dedup(items, key=None):
    out = []
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
            out.append(item)
    return out
