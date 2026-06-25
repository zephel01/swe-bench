def toposort(nodes, edges):
    order = []
    state = {}

    def visit(node, stack):
        st = state.get(node)
        if st == 1:
            return
        if st == 0:
            raise ValueError("cycle: " + " -> ".join(stack + [node]))
        state[node] = 0
        for dep in edges.get(node, []):
            visit(dep, stack + [node])
        state[node] = 1
        order.append(node)

    for node in sorted(nodes):
        visit(node, [])
    return order
