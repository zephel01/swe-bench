from datetime import datetime, timezone

from nextrun import next_run
from ordering import order_due

UTC = timezone.utc


def test_priority_distinct_order():
    jobs = [
        {"name": "a", "priority": 1, "seq": 0},
        {"name": "b", "priority": 5, "seq": 1},
        {"name": "c", "priority": 3, "seq": 2},
    ]
    assert order_due(jobs) == ["b", "c", "a"]


def test_utc_next_run_rolls_to_next_day():
    now = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    assert next_run(now, 8, 0, 0) == datetime(2026, 3, 11, 8, 0, tzinfo=UTC)


def test_utc_next_run_later_today():
    now = datetime(2026, 3, 10, 6, 0, tzinfo=UTC)
    assert next_run(now, 8, 0, 0) == datetime(2026, 3, 10, 8, 0, tzinfo=UTC)
