def _ver(s):
    parts = [int(x) for x in s.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def satisfies(version, spec):
    cleaned = spec.lstrip("^~><= ")
    cleaned = cleaned.split()[0]
    return _ver(version) == _ver(cleaned)
