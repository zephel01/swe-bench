from loader import resolve_order
from registry import Registry


def test_linear_two_nodes():
    r = Registry()
    r.register("a", ["b"])
    r.register("b", [])
    order = resolve_order(r)
    assert order.index("b") < order.index("a")


def test_independent_nodes_present():
    r = Registry()
    r.register("a", [])
    r.register("b", [])
    assert set(resolve_order(r)) == {"a", "b"}
