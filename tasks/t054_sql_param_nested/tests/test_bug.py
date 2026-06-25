from builder import build


def test_nested_and_collects_params():
    sql, params = build(("and", [("eq", "a", 1), ("eq", "b", 2)]))
    assert sql.count("?") == 2
    assert params == [1, 2]


def test_between_collects_two_params_in_order():
    sql, params = build(("between", "age", 18, 65))
    assert sql == "age BETWEEN ? AND ?"
    assert params == [18, 65]


def test_not_wraps_and_keeps_params():
    sql, params = build(("not", ("eq", "a", 5)))
    assert sql == "NOT (a = ?)"
    assert params == [5]


def test_deep_mixed_param_order_no_interpolation():
    evil = "x'; DROP TABLE t;--"
    cond = ("or", [
        ("and", [("eq", "name", evil), ("between", "age", 18, 65)]),
        ("not", ("in", "id", [7, 8])),
    ])
    sql, params = build(cond)
    assert evil not in sql
    assert sql.count("?") == 5
    assert params == [evil, 18, 65, 7, 8]
