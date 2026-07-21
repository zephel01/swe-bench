# search() signature migration

Our legacy client code calls `search(q, filters)` all over the place.
We need to add a new `search(SearchRequest)` entry point without breaking
any of the existing call sites.

Requirements:

- `search("python")` and `search("python", {"category": "book"})` must
  keep returning the same results as before (with no exceptions).
- A new `search(SearchRequest(q=..., filters=..., limit=..., offset=...))`
  form must also work, and be the recommended path for new code.
- Internally there should be a single implementation; both surfaces
  delegate to it.
- Legacy calls should emit a `DeprecationWarning` via a dedicated
  `LegacySearchDeprecated` subclass so we can track migration progress.
- `SearchRequest`, `search`, and `LegacySearchDeprecated` must all be
  exported from the package's `__all__`.

Please extend the code so the tests in `tests/` all pass.
