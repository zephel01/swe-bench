from dialect import PostgresDialect
from query import build_select, build_where_in


def test_pg_select_numbered_placeholders():
    sql, params = build_select("u", {"a": 1, "b": 2}, PostgresDialect())
    assert sql == "SELECT * FROM u WHERE a = $1 AND b = $2"
    assert params == [1, 2]


def test_pg_in_numbered():
    sql, params = build_where_in("id", [10, 20, 30], PostgresDialect())
    assert sql == "id IN ($1, $2, $3)"
    assert params == [10, 20, 30]


def test_values_are_not_interpolated():
    evil = "1); DROP TABLE users;--"
    sql, params = build_select("u", {"name": evil}, PostgresDialect())
    assert evil not in sql
    assert params == [evil]
    assert sql == "SELECT * FROM u WHERE name = $1"
