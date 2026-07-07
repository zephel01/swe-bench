"""Group rows by a composite key and average each group's values."""

from stats import mean


def aggregate(rows):
    """Group ``rows`` by the ``(g, s)`` pair and return the mean ``v`` per group.

    Each row is a dict with keys ``"g"``, ``"s"`` and ``"v"``. The returned
    mapping is keyed by the ``(g, s)`` tuple.
    """
    groups = {}
    for row in rows:
        key = row["g"] + row["s"]
        groups.setdefault(key, []).append(row["v"])
    return {key: mean(values) for key, values in groups.items()}
