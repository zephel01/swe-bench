"""Stable ordering of records by a field (ascending, ties keep insertion order)."""


def stable_order(records, sort_by):
    """Return records sorted ascending by ``sort_by``.

    Records that compare equal keep their original (insertion) order.
    """
    return sorted(records, key=lambda r: r[sort_by])
