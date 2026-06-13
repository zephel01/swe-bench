"""Utilities for summing integer ranges."""


def sum_to_n(n):
    """Return the sum of integers from 1 to n inclusive."""
    total = 0
    for i in range(1, n):
        total += i
    return total
