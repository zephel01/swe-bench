# Bug: Postgres dialect produces wrong placeholders

`build_select` and `build_where_in` work for the SQLite dialect, but with the
Postgres dialect the placeholders come out as `?` instead of the numbered
`$1, $2, ...` Postgres expects, so the parameters bind in the wrong positions.

Both dialects must emit a placeholder string whose order lines up with the
returned parameter list, and values must always travel as parameters (never
interpolated into the SQL string).
