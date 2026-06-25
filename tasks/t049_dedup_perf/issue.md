# Bug: deduplication is slow and breaks on unhashable items

`dedup(items)` must keep the first occurrence of each element in input order.
Two problems:

- It does not scale: a list of ~40k unique hashable elements (each appearing
  twice) does not finish in time.
- The input may also contain **unhashable** elements (e.g. dicts or lists);
  these must still be de-duplicated by equality, and a list may freely mix
  hashable and unhashable items.

Keep the order-preserving behavior, run in (near) linear time for hashable
elements, and handle unhashable elements correctly.
