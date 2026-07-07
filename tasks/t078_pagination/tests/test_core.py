from query import query


def _all(_r):
    return True


def test_page_one():
    recs = [{"id": i, "k": i} for i in range(5)]
    assert [r["id"] for r in query(recs, _all, "k", 1, 2)] == [0, 1]


def test_page_two():
    recs = [{"id": i, "k": i} for i in range(5)]
    assert [r["id"] for r in query(recs, _all, "k", 2, 2)] == [2, 3]


def test_sort_distinct_values():
    recs = [{"id": 1, "k": 30}, {"id": 2, "k": 10}, {"id": 3, "k": 20}]
    assert [r["id"] for r in query(recs, _all, "k", 1, 10)] == [2, 3, 1]
