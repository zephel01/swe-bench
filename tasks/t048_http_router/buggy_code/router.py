from params import convert  # noqa: F401


def _match(pattern, path):
    psegs = pattern.strip("/").split("/")
    parts = path.strip("/").split("/")
    params = {}
    i = 0
    for j, seg in enumerate(psegs):
        if seg.startswith("{") and seg.endswith("}"):
            name, _, typ = seg[1:-1].partition(":")
            if typ == "*":
                params[name] = "/".join(parts[i:])
                return params
            if i >= len(parts):
                return None
            params[name] = parts[i]
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
        for pattern, handler in self.routes:
            params = _match(pattern, path)
            if params is not None:
                return handler, params
        return None, None
