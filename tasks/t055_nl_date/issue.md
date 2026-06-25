# Bug: relative date phrases are mis-parsed

`parse(text, base)` handles absolute ISO dates and `today`/`tomorrow`/
`yesterday`, but relative phrases are wrong or unsupported. Some examples, with
`base = 2026-06-26` (a Friday):

- `parse("next friday", base)` should be `2026-07-03` (the *following* Friday,
  not today).
- `parse("next monday", base)` should be `2026-06-29`.
- `parse("in 3 days", base)` should be `2026-06-29`.
- Parsing should be case-insensitive (`"Next Monday"` works too).

Figure out reasonable semantics for these phrases. Absolute dates and
today/tomorrow/yesterday already work.
