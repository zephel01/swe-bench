# Rendered tables don't line up and have ragged trailing spaces

`format_table(headers, rows)` renders a fixed-width text table with columns
separated by ` | `. Two layout problems show up:

- When a column's header is wider than every value in that column, the rows no
  longer line up under the header — the columns are visibly misaligned.
- Rows come back with trailing spaces at the end of the line, so lines that
  should be clean have padding hanging off the right edge.

Tables where every column's values are at least as wide as the header, and
where nothing needs right-padding, look correct.
