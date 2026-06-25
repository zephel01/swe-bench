# Bug: config merge mishandles nested/edge cases

Merging two config dicts gets several cases wrong: nested lists are not
concatenated, an explicit `None` on the right is dropped instead of overriding,
and a type change between sides is mishandled.

Intended rules (applied at every depth): dicts merge recursively; lists from
both sides concatenate (including nested lists); any other value on the right
replaces the left — including dict-over-scalar, scalar-over-dict, and an explicit
`None`. Flat scalar replace, disjoint keys, and one-level dict merge already work.
