def _ver(s):
    parts = [int(x) for x in s.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _cmp(version, target, op):
    if op == ">=":
        return version >= target
    if op == "<=":
        return version <= target
    if op == ">":
        return version > target
    if op == "<":
        return version < target
    return version == target


def _match_clause(version, clause):
    if clause.startswith("^"):
        base = _ver(clause[1:])
        if base[0] > 0:
            upper = (base[0] + 1, 0, 0)
        elif base[1] > 0:
            upper = (0, base[1] + 1, 0)
        else:
            upper = (0, 0, base[2] + 1)
        return base <= version < upper
    if clause.startswith("~"):
        base = _ver(clause[1:])
        upper = (base[0], base[1] + 1, 0)
        return base <= version < upper
    for op in (">=", "<=", ">", "<", "="):
        if clause.startswith(op):
            return _cmp(version, _ver(clause[len(op):]), op)
    return version == _ver(clause)


def satisfies(version, spec):
    v = _ver(version)
    return all(_match_clause(v, clause) for clause in spec.split())
