"""Daily temperature summary (in Fahrenheit)."""

from convert import c_to_f


def daily_summary(readings_c):
    """Average of the readings converted to Fahrenheit.

    None entries are missing sensors and must be ignored.
    Returns None when there is no valid reading.
    """
    fs = [c_to_f(c) for c in readings_c if c is not None]
    # BUG: divides by the full length (counts ignored None entries),
    # and crashes on an empty list instead of returning None.
    return round(sum(fs) / len(readings_c), 1)
