from params import convert


def _specificity(pattern):
    score = 0
    for seg in pattern.strip("/").split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            score += 0 if seg[1:-1].endswith(":*") else 1
        else:
            score += 2
    return score


def _match(pattern, path):
    psegs = pattern.strip("/").split("/")
    parts = path.strip("/").split("/")
    params = {}
    i = 0
    for j, seg in enumerate(psegs):
        if seg.startswith("{") and seg.endswith("}"):
            name, _, typ = seg[1:-1].partition(":")
            if typ == "*":
                if j != len(psegs) - 1:
                    return None
                params[name] = "/".join(parts[i:])
                return params
            if i >= len(parts):
                return None
            params[name] = convert(typ, parts[i])
            i += 1
        else:
            if i >= len(parts) or parts[i] != seg:
                return None
            i += 1
    if i != len(parts):
        return None
    return params


class Router:
    def __init__(self):
        self.routes = []

    def add(self, pattern, handler):
        self.routes.append((pattern, handler))

    def match(self, path):
        ordered = sorted(self.routes, key=lambda r: _specificity(r[0]), reverse=True)
        for pattern, handler in ordered:
            params = _match(pattern, path)
            if params is not None:
                return handler, params
        return None, None
