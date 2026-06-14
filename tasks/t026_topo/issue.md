# Bug: a graph with a cycle returns a list instead of being rejected

`toposort({"a": ["b"], "b": ["a"]})` returns a (truncated) list. A graph that
contains a cycle has no valid ordering and must be rejected with a `ValueError`
rather than producing a partial result.

Acyclic graphs already return a correct, lexicographically-stable order.
