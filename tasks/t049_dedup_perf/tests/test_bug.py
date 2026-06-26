import time

from dedup import dedup


def test_key_function_first_wins():
    pairs = [("a", 1), ("a", 2), ("b", 3), ("a", 4)]
    assert dedup(pairs, key=lambda t: t[0]) == [("a", 1), ("b", 3)]


def test_key_with_unhashable_items():
    rows = [{"id": 1, "v": "x"}, {"id": 1, "v": "y"}, {"id": 2, "v": "z"}]
    assert dedup(rows, key=lambda r: r["id"]) == [
        {"id": 1, "v": "x"},
        {"id": 2, "v": "z"},
    ]


def test_large_input_is_fast():
    data = list(range(40_000)) * 2
    start = time.perf_counter()
    out = dedup(data)
    assert out == list(range(40_000))
    assert time.perf_counter() - start < 1.0
