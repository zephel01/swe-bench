# Bug: single-assignment result cell accepts two winners

`ResultCell` is a one-shot result holder: the first caller of `set(value)` wins
and gets back `True`; every later `set` is a no-op that returns `False` and
leaves the stored value untouched. Consumers rely on exactly one `set` ever
returning `True` (that thread owns follow-up work). In a single thread this
holds. But when two threads race to `set` a fresh cell, both sometimes get
`True`, the stored value flip-flops, and the "exactly one winner" contract is
violated.

For any cell, at most one `set` call may ever return `True`; all others must
return `False` and must not overwrite the winning value.
