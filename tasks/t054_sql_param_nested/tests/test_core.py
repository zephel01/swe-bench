from builder import build


def test_single_eq_sqlite():
    sql, params = build(("eq", "a", 1))
    assert sql == "a = ?"
    assert params == [1]


def test_single_in_sqlite():
    sql, params = build(("in", "b", [1, 2, 3]))
    assert sql == "b IN (?, ?, ?)"
    assert params == [1, 2, 3]
