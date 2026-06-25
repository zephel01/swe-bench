from builder import build


def test_nested_and_collects_params():
    cond = ("and", [("eq", "a", 1), ("eq", "b", 2)])
    sql, params = build(cond)
    assert sql.count("?") == 2
    assert params == [1, 2]


def test_nested_or_in_collects_params():
    cond = ("or", [("eq", "a", 1), ("in", "b", [2, 3])])
    sql, params = build(cond)
    assert sql.count("?") == 3
    assert params == [1, 2, 3]


def test_no_value_interpolation_when_nested():
    evil = "x'; DROP TABLE t;--"
    cond = ("and", [("eq", "name", evil), ("eq", "ok", 1)])
    sql, params = build(cond)
    assert evil not in sql
    assert evil in params
    assert sql.count("?") == 2
