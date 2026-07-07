# Spreadsheet cell ranges expand to the wrong cells

We convert between spreadsheet column labels (A, B, ..., Z, AA, ...) and
numbers, and expand ranges like `A1:B2` into the list of cells they cover.
Two things are wrong:

- Turning a column number back into a label is off: `num_to_col(1)` does not
  give `"A"`, and multi-letter labels like `AA` are wrong too.
- Expanding a rectangular range drops its last row and last column, so
  `expand_range("A1:B2")` comes back missing cells.

Converting a label to a number and parsing a single cell reference look fine.
