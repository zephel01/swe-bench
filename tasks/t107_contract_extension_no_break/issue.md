# Add a `strict` mode to `parse()` without breaking existing callers

## Background

Our config parser exposes a single entry point:

```python
from parser import parse

parse(text)
```

It accepts a small line-oriented format:

- `KEY=VALUE` — assignment (whitespace around `=` is trimmed)
- `@unset KEY` — remove a key
- Lines starting with `#` and blank lines are ignored
- Anything else is silently ignored; duplicate keys silently overwrite

Many production call sites rely on this lenient behavior.

## Request

Add an optional keyword argument `strict: bool = False` to `parse`.

- `strict=False` (the default) must behave **exactly** like today.
  Every existing call site — including calls that pass no `strict`
  argument at all — must keep returning the same dict.
- `strict=True` must raise **specific** exceptions:
  - `DuplicateKeyError` when the same key is assigned more than once
  - `UnknownDirectiveError` when an `@directive` is not recognized
  - `SyntaxError` when a line is neither a comment, blank, directive,
    nor a valid `KEY=VALUE` assignment

All three specific errors must inherit from `ParseError` so callers
can still `except ParseError:` catch-all. The `exceptions` module must
export `ParseError`, `SyntaxError`, `DuplicateKeyError`, and
`UnknownDirectiveError`.

## Acceptance criteria

1. Every existing call site (no `strict` kwarg) keeps working.
2. `parse(text, strict=True)` raises the specific subclass for each
   category of problem — using a single generic `ParseError` for all
   of them is **not** enough.
3. All specific errors inherit from `ParseError`.
