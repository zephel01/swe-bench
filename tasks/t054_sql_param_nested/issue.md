# Bug: nested conditions interpolate values instead of parameterizing

`build(cond)` parameterizes a single `eq`/`in` condition correctly, but once you
nest them under `and`/`or` the values are interpolated straight into the SQL
string and the parameter list comes back empty — an injection risk.

Walk the condition tree to any depth, emit one placeholder per value, and return
all values in the parameter list in order. Never interpolate a value.
