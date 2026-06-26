# Bug: merge replaces nested lists and mutates its inputs

`merge(a, b)` should deep-merge config: dicts merge recursively, lists from both
sides concatenate (at any depth), and any other value on the right replaces the
left (including dict-over-scalar and scalar-over-dict). Two faults:

- nested lists are replaced instead of concatenated;
- the function mutates its arguments in place — callers' original `a` (and its
  nested dicts) must be left unchanged; `merge` must return a fresh structure.

Flat scalar replace, disjoint keys, and one-level dict merge already work.
