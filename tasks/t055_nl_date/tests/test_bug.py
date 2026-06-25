import datetime

from nldate import parse

BASE = datetime.date(2026, 6, 26)  # a Friday


def test_next_friday_is_strictly_next_week():
    # base itself is Friday; "next friday" must be +7, not today
    assert parse("next friday", BASE) == datetime.date(2026, 7, 3)


def test_next_monday():
    assert parse("next monday", BASE) == datetime.date(2026, 6, 29)


def test_in_n_days():
    assert parse("in 3 days", BASE) == datetime.date(2026, 6, 29)


def test_case_insensitive():
    assert parse("Next Monday", BASE) == datetime.date(2026, 6, 29)
