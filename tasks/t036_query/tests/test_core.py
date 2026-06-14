from builder import Query


def test_simple_where():
    sql, params = Query("t").where("a", "=", 1).build()
    assert sql == "SELECT * FROM t WHERE a = ?"
    assert params == [1]


def test_select_columns_and_and():
    sql, params = Query("t").select("a", "b").where("a", "=", 1).where("b", ">", 2).build()
    assert sql == "SELECT a, b FROM t WHERE a = ? AND b > ?"
    assert params == [1, 2]


def test_no_where():
    sql, params = Query("t").build()
    assert sql == "SELECT * FROM t"
    assert params == []
