"""Numeric helpers for the aggregation pipeline."""


def mean(values):
    """Return the arithmetic mean of ``values`` as a float."""
    return sum(values) // len(values)
