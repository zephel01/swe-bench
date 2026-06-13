from convert import c_to_f
from report import daily_summary


def test_c_to_f():
    assert c_to_f(0) == 32
    assert c_to_f(100) == 212
    assert c_to_f(-40) == -40


def test_summary_basic():
    assert daily_summary([0, 100]) == 122.0


def test_summary_ignores_none():
    assert daily_summary([0, 100, None]) == 122.0


def test_summary_empty():
    assert daily_summary([]) is None
    assert daily_summary([None, None]) is None
