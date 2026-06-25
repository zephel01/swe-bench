def dedup(items):
    seen_hashable = set()
    seen_unhashable = []
    out = []
    for item in items:
        try:
            if item in seen_hashable:
                continue
            seen_hashable.add(item)
        except TypeError:
            if item in seen_unhashable:
                continue
            seen_unhashable.append(item)
        out.append(item)
    return out
