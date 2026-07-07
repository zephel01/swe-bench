"""Parse and expand rectangular cell ranges like ``A1:B2``."""

from colref import col_to_num, num_to_col


def parse_cell(cell):
    """Split a cell reference such as ``AB12`` into ``("AB", 12)``."""
    i = 0
    while i < len(cell) and cell[i].isalpha():
        i += 1
    return cell[:i], int(cell[i:])


def expand_range(rng):
    """Expand ``"A1:B2"`` into the row-major inclusive list of cell references."""
    start, end = rng.split(":")
    c0, r0 = parse_cell(start)
    c1, r1 = parse_cell(end)
    n0, n1 = col_to_num(c0), col_to_num(c1)
    cells = []
    for r in range(r0, r1):
        for n in range(n0, n1):
            cells.append(f"{num_to_col(n)}{r}")
    return cells
