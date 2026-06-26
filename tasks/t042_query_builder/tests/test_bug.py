from dialect import PostgresDialect
from query import build_select


def test_pg_multiple_eq_numbered():
    sql, params = build_select("u", {"a": 1, "b": 2}, PostgresDialect())
    assert sql == "SELECT * FROM u WHERE a = $1 AND b = $2"
    assert params == [1, 2]


def test_pg_eq_and_in_continuous_numbering():
    sql, params = build_select(
        "u", {"a": 1}, PostgresDialect(), in_clause=("id", [7, 8, 9])
    )
    assert sql == "SELECT * FROM u WHERE a = $1 AND id IN ($2, $3, $4)"
    assert params == [1, 7, 8, 9]
