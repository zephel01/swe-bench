"""Calendar helpers."""

_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def is_leap_year(year):
    """Return True if year is a Gregorian leap year."""
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return year % 4 == 0


def days_in_month(year, month):
    """Return the number of days in the given month (1-12)."""
    if month == 2 and is_leap_year(year):
        return 29
    return _DAYS[month - 1]
