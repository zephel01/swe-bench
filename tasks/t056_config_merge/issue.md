# Bug: config merge clobbers nested structures

Merging two config dicts uses a shallow update, so a nested dict on the right
replaces the whole nested dict on the left, and lists are replaced instead of
combined.

The intended rules, inferred from how configs are layered: dicts merge
recursively, lists from both sides are concatenated, and a scalar (or a
different type) on the right replaces the left value. Flat scalar replacement and
disjoint keys already work.
