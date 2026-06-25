# Bug: deduplication is too slow on large inputs

`dedup(items)` must remove duplicates while keeping the first occurrence of each
element, in input order. It is correct on small inputs but does not scale: a
list of ~10k unique elements (each appearing twice) does not finish in time.

Keep the order-preserving behavior and make it run in linear time.
