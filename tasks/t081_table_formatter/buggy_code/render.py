"""Fixed-width text table rendering."""

from widths import col_widths


def format_table(headers, rows):
    """Render ``headers`` and ``rows`` as an aligned ` | `-separated table."""
    widths = col_widths(headers, rows)
    lines = []
    for row in [headers, *rows]:
        cells = [row[c].ljust(widths[c]) for c in range(len(widths))]
        lines.append(" | ".join(cells))
    return "\n".join(lines)
