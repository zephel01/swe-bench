# Bug: nested conditions interpolate values instead of parameterizing

`build(cond)` parameterizes a single `eq`/`in`, but other node types and any
nesting fall back to interpolating values straight into the SQL string with an
empty parameter list — an injection risk. Affected: `and`/`or`, `not`, and
`between` (which contributes two params, `lo` then `hi`).

Walk the condition tree to any depth, emit one placeholder per value, and return
every value in the parameter list in left-to-right order. Never interpolate.
