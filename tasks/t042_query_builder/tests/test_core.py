from dialect import SQLiteDialect
from query import build_select, build_where_in


def test_sqlite_select_single():
    sql, params = build_select("users", {"id": 5}, SQLiteDialect())
    assert sql == "SELECT * FROM users WHERE id = ?"
    assert params == [5]


def test_sqlite_select_multi():
    sql, params = build_select("u", {"a": 1, "b": 2}, SQLiteDialect())
    assert sql == "SELECT * FROM u WHERE a = ? AND b = ?"
    assert params == [1, 2]


def test_sqlite_in():
    sql, params = build_where_in("id", [1, 2, 3], SQLiteDialect())
    assert sql == "id IN (?, ?, ?)"
    assert params == [1, 2, 3]
