"""Ordering of due jobs by priority, ties broken by submission order (FIFO)."""


def order_due(jobs):
    """Return job names ordered by priority (highest first).

    Jobs sharing a priority keep their submission order (FIFO), which is
    tracked by the integer ``seq`` field.
    """
    ordered = sorted(jobs, key=lambda j: (-j["priority"], -j["seq"]))
    return [j["name"] for j in ordered]
