"""Context window computation for diff hunks."""


def context_window(n_lines, start, end, context):
    """Return the ``[lo, hi)`` line range covering ``[start, end)`` plus context.

    ``context`` lines are included on each side, clamped to ``[0, n_lines]``.
    """
    lo = max(0, start - context)
    hi = min(n_lines, end + context - 1)
    return lo, hi
