"""Numeric clamping helpers."""


def clamp(value, low, high):
    """Clamp value into the inclusive range [low, high]."""
    if value < low:
        return high
    if value > high:
        return high
    return value
