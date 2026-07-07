"""Filter -> sort -> paginate pipeline."""

from order import stable_order


def query(records, keep, sort_by, page, per_page):
    """Return one page of records.

    The pipeline filters with ``keep`` first, then sorts the survivors, then
    slices out the 1-based ``page`` of size ``per_page``.
    """
    ordered = stable_order(records, sort_by)
    start = (page - 1) * per_page
    page_items = ordered[start:start + per_page]
    return [r for r in page_items if keep(r)]
