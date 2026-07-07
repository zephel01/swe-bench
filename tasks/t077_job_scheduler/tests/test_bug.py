from datetime import datetime, timezone

from nextrun import next_run
from ordering import order_due

UTC = timezone.utc


def test_same_priority_keeps_fifo():
    jobs = [
        {"name": "first", "priority": 5, "seq": 0},
        {"name": "second", "priority": 5, "seq": 1},
        {"name": "third", "priority": 5, "seq": 2},
    ]
    assert order_due(jobs) == ["first", "second", "third"]


def test_next_run_respects_timezone():
    now = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    # daily at 08:00 in UTC+9 -> correct next run is 2026-03-10 23:00 UTC
    assert next_run(now, 8, 0, 9) == datetime(2026, 3, 10, 23, 0, tzinfo=UTC)
