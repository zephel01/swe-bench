def dedup(items, key=None):
    keyf = key or (lambda x: x)
    seen_hashable = set()
    seen_unhashable = []
    out = []
    for item in items:
        k = keyf(item)
        try:
            if k in seen_hashable:
                continue
            seen_hashable.add(k)
        except TypeError:
            if k in seen_unhashable:
                continue
            seen_unhashable.append(k)
        out.append(item)
    return out
