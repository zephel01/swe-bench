"""A tiny plugin registry."""

_REGISTRY = {}


def register(name):
    """Decorator: register the decorated function under `name`."""
    def deco(fn):
        _REGISTRY[name] = fn
        return fn
    return deco


def get(name):
    return _REGISTRY.get(name)


def available():
    return sorted(_REGISTRY)
