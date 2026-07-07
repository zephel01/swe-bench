from query import query


def _all(_r):
    return True


def _even(r):
    return r["id"] % 2 == 0


def test_offset_computed_after_filter():
    recs = [{"id": i, "k": i} for i in range(10)]
    got = [r["id"] for r in query(recs, _even, "k", 1, 3)]
    assert got == [0, 2, 4]


def test_stable_sort_preserves_insertion_order_on_ties():
    recs = [{"id": 1, "k": 5}, {"id": 2, "k": 5}, {"id": 3, "k": 5}]
    got = [r["id"] for r in query(recs, _all, "k", 1, 10)]
    assert got == [1, 2, 3]
