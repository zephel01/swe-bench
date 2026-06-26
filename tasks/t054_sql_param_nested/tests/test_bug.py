from builder import PostgresDialect, build


def test_nested_collects_params_sqlite():
    cond = ("or", [("eq", "a", 1), ("in", "b", [2, 3])])
    sql, params = build(cond)
    assert sql.count("?") == 3
    assert params == [1, 2, 3]
    assert "1" not in sql


def test_nested_pg_global_numbering():
    cond = ("and", [
        ("eq", "a", 1),
        ("or", [("eq", "b", 2), ("in", "c", [3, 4])]),
    ])
    sql, params = build(cond, PostgresDialect())
    assert sql == "(a = $1) AND ((b = $2) OR (c IN ($3, $4)))"
    assert params == [1, 2, 3, 4]


def test_no_interpolation_when_nested():
    evil = "x'; DROP TABLE t;--"
    sql, params = build(("and", [("eq", "name", evil), ("eq", "ok", 1)]))
    assert evil not in sql
    assert params == [evil, 1]
