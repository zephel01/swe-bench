"""Bijective base-26 conversion between column labels and numbers (A == 1)."""


def col_to_num(col):
    """Convert a column label (``A``, ``Z``, ``AA``, ...) to its 1-based number."""
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def num_to_col(n):
    """Convert a 1-based column number back to its label."""
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))
