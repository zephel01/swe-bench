"""Column width computation for the text table formatter."""


def col_widths(headers, rows):
    """Return each column's display width (max of the header and all cells)."""
    widths = []
    for c in range(len(headers)):
        w = len(headers[c])
        for row in rows:
            w = max(w, len(row[c]))
        widths.append(w)
    return widths
