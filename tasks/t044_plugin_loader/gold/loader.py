from registry import Registry  # noqa: F401


class CycleError(Exception):
    pass


def resolve_order(registry):
    order = []
    state = {}  # name -> 0 visiting, 1 done

    def visit(name, stack):
        st = state.get(name)
        if st == 1:
            return
        if st == 0:
            raise CycleError("cycle: " + " -> ".join(stack + [name]))
        state[name] = 0
        for dep in registry.deps(name):
            visit(dep, stack + [name])
        state[name] = 1
        order.append(name)

    for name in sorted(registry.names()):
        visit(name, [])
    return order
