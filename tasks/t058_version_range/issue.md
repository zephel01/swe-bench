# Bug: only exact version matches work

`satisfies(version, spec)` treats every spec as an exact match: caret (`^`),
tilde (`~`), comparison operators, and compound (space-separated AND) ranges are
not honored. Expected semver semantics:

- `^1.2.0` means `>=1.2.0 <2.0.0`; for a `0.x` version, `^0.2.0` means
  `>=0.2.0 <0.3.0`.
- `~1.2.0` means `>=1.2.0 <1.3.0`.
- `">=1.0.0 <2.0.0"` is an AND of both clauses.

Exact matching already works.
