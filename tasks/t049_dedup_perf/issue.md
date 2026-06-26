# Bug: dedup ignores the key function, is slow, and breaks on unhashable

`dedup(items, key=None)` keeps the first occurrence of each element in order.
Problems:

- The optional `key` callable is ignored — items are compared whole instead of
  by `key(item)`, so de-duplication by a field does not work.
- It does not scale: ~40k unique elements (each twice) do not finish in time.
- Items (or their keys) may be **unhashable** (dicts/lists); these must still
  de-duplicate by equality.

Keep first-occurrence order, run in (near) linear time for hashable keys, honor
`key`, and handle unhashable keys.
