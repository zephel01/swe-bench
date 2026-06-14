from builder import Query


def test_where_in_is_parameterized():
    sql, params = Query("t").where_in("id", [10, 20, 30]).build()
    assert sql == "SELECT * FROM t WHERE id IN (?, ?, ?)"
    assert params == [10, 20, 30]
