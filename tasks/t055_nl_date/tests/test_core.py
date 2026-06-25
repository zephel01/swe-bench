import datetime

from nldate import parse

BASE = datetime.date(2026, 6, 26)  # a Friday


def test_iso_date():
    assert parse("2026-07-01", BASE) == datetime.date(2026, 7, 1)


def test_today_tomorrow_yesterday():
    assert parse("today", BASE) == BASE
    assert parse("tomorrow", BASE) == datetime.date(2026, 6, 27)
    assert parse("yesterday", BASE) == datetime.date(2026, 6, 25)
