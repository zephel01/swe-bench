"""Searching utilities."""


def binary_search(items, target):
    """Return the index of target in sorted items, or -1 if absent."""
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
