from registry import Registry  # noqa: F401


class CycleError(Exception):
    pass


def resolve_order(registry):
    order = []
    for name in registry.names():
        for dep in registry.deps(name):
            if dep not in order:
                order.append(dep)
        if name not in order:
            order.append(name)
    return order
