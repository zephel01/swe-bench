# Bug: nested conditions interpolate, and PG numbering is missing

`build(cond, dialect)` parameterizes a single `eq`/`in`, but two things fail:

- Once conditions nest under `and`/`or`, values are interpolated straight into
  the SQL string with an empty parameter list (injection risk).
- With the Postgres dialect, placeholders must be a single running `$1, $2, ...`
  counter threaded through the whole (recursive) tree; today nested nodes don't
  use the dialect at all.

Walk the tree to any depth, emit one placeholder per value with continuous
numbering, and return all values in left-to-right order. SQLite single
conditions already work.
