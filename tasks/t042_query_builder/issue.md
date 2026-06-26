# Bug: Postgres placeholders are wrong (numbering)

`build_select` supports equality conditions and an optional `IN` clause. With
the Postgres dialect two things break:

- equality conditions all render as `$1` instead of `$1, $2, ...`;
- the `IN` clause restarts placeholder numbering (and ignores the dialect),
  instead of continuing the running index after the equality params.

Placeholders must be numbered with a single running counter across all clauses
so they line up with the parameter list in order. SQLite (`?`) already works.
