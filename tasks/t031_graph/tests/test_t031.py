from graph import shortest_path


def _g():
    return {
        "a": {"b": 1, "c": 4},
        "b": {"c": 1, "d": 5},
        "c": {"d": 1},
        "d": {},
    }


def test_plain_shortest():
    assert shortest_path(_g(), "a", "d") == 3      # a-b-c-d


def test_forbidden_forces_detour():
    # 最短の b->c を禁止 → a-b-d(6) か a-c-d(5) で 5
    assert shortest_path(_g(), "a", "d", forbidden={("b", "c")}) == 5


def test_unreachable_is_none():
    assert shortest_path({"a": {}, "b": {}}, "a", "b") is None


def test_forbidden_makes_unreachable():
    g = {"a": {"b": 1}, "b": {}}
    assert shortest_path(g, "a", "b", forbidden={("a", "b")}) is None
