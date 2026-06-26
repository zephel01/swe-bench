from dialect import SQLiteDialect
from query import build_select


def test_sqlite_single_eq():
    sql, params = build_select("u", {"id": 5}, SQLiteDialect())
    assert sql == "SELECT * FROM u WHERE id = ?"
    assert params == [5]


def test_sqlite_in_only():
    sql, params = build_select("u", {}, SQLiteDialect(), in_clause=("id", [1, 2]))
    assert sql == "SELECT * FROM u WHERE id IN (?, ?)"
    assert params == [1, 2]
