# Bug: add_tag() accumulates tags across unrelated calls

Calling `add_tag("a")` then `add_tag("b")` (each without passing a list)
returns `["a", "b"]` for the second call instead of `["b"]`.
State leaks between independent calls.
