from builder import build


def test_single_eq():
    sql, params = build(("eq", "a", 1))
    assert sql == "a = ?"
    assert params == [1]


def test_single_in():
    sql, params = build(("in", "b", [1, 2, 3]))
    assert sql == "b IN (?, ?, ?)"
    assert params == [1, 2, 3]
