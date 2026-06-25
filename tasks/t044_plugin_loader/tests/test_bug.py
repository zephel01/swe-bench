import pytest

from loader import CycleError, resolve_order
from registry import Registry


def _chain():
    r = Registry()
    r.register("c", ["b"])
    r.register("b", ["a"])
    r.register("a", [])
    return r


def test_transitive_order():
    order = _chain()
    res = resolve_order(order)
    assert res.index("a") < res.index("b") < res.index("c")


def test_cycle_detected():
    r = Registry()
    r.register("a", ["b"])
    r.register("b", ["a"])
    with pytest.raises(CycleError):
        resolve_order(r)


def test_order_independent_of_registration():
    r1 = Registry()
    for name, deps in [("d", ["b", "c"]), ("b", ["a"]), ("c", ["a"]), ("a", [])]:
        r1.register(name, deps)
    r2 = Registry()
    for name, deps in [("a", []), ("c", ["a"]), ("b", ["a"]), ("d", ["b", "c"])]:
        r2.register(name, deps)
    assert resolve_order(r1) == resolve_order(r2)
