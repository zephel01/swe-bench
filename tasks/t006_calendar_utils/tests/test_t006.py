from calendar_utils import days_in_month, is_leap_year


def test_century_not_leap():
    assert not is_leap_year(1900)
    assert not is_leap_year(2100)


def test_400_leap():
    assert is_leap_year(2000)
    assert is_leap_year(1600)


def test_regular():
    assert is_leap_year(2024)
    assert not is_leap_year(2023)


def test_february():
    assert days_in_month(1900, 2) == 28
    assert days_in_month(2000, 2) == 29
    assert days_in_month(2024, 2) == 29


def test_other_months():
    assert days_in_month(2023, 1) == 31
    assert days_in_month(2023, 4) == 30
