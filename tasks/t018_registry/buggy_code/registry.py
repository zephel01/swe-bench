"""A tiny plugin registry."""

_REGISTRY = {}


def register(name):
    """Decorator: register the decorated function under `name`."""
    def deco(fn):
        # BUG: stores the name string instead of the function
        _REGISTRY[name] = name
        return fn
    return deco


def get(name):
    return _REGISTRY.get(name)


def available():
    return sorted(_REGISTRY)
