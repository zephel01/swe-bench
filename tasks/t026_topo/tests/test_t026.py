import pytest

from topo import toposort


def test_diamond_lexicographic():
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
    assert toposort(g) == ["a", "b", "c", "d"]


def test_independent_nodes_sorted():
    g = {"x": [], "a": [], "m": []}
    assert toposort(g) == ["a", "m", "x"]


def test_successor_only_node_included():
    assert toposort({"a": ["b"]}) == ["a", "b"]


def test_cycle_raises():
    with pytest.raises(ValueError):
        toposort({"a": ["b"], "b": ["a"]})


def test_self_loop_raises():
    with pytest.raises(ValueError):
        toposort({"a": ["a"]})
