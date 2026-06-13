"""Basic statistics helpers."""


def average(values):
    """Return the arithmetic mean of values, or 0.0 for an empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)
