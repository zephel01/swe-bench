"""Filter -> sort -> paginate pipeline."""

from order import stable_order


def query(records, keep, sort_by, page, per_page):
    """Return one page of records.

    The pipeline filters with ``keep`` first, then sorts the survivors, then
    slices out the 1-based ``page`` of size ``per_page``.
    """
    filtered = [r for r in records if keep(r)]
    ordered = stable_order(filtered, sort_by)
    start = (page - 1) * per_page
    return ordered[start:start + per_page]
