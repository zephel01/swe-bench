# Bug: redoing after new edits resurrects abandoned commands

Our undo/redo `History` is a single linear timeline. After undoing, doing new
work is supposed to abandon the redo branch -- the undone commands should be
unreachable once you have edited on top of the point you undid to.

Reproduce:
1. `apply(Append(doc, "a"))`, `apply(Append(doc, "b"))` -> `doc == ["a", "b"]`.
2. `undo()` -> `doc == ["a"]` (b is on the redo branch).
3. `apply(Append(doc, "c"))` -> `doc == ["a", "c"]`.
4. `redo()`.

Observed:
- After step 3, `can_redo()` still returns `True`.
- Step 4 re-applies the abandoned `b`, leaving `doc == ["a", "c", "b"]`.

Expected: applying `c` discards the redo branch, so `can_redo()` is `False` and
`redo()` is a no-op (`doc` stays `["a", "c"]`). Plain linear undo/redo and
grouped undo/redo behave correctly; only a single (non-grouped) command applied
after an undo fails to clear the redo branch.
