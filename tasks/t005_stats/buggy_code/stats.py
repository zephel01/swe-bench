"""Basic statistics helpers."""


def average(values):
    """Return the arithmetic mean of values, or 0.0 for an empty list."""
    return sum(values) / len(values)
