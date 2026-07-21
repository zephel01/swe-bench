# CSV Dialect Auto-Detection: Three Independent Bugs

We ship three tiny helpers that infer a CSV file's dialect from a text
sample. Together they answer the question "how is this file laid out?":

- `detect_quotechar(sample)` — `quote_detect.py`
- `detect_delimiter(sample, quotechar)` — `delim_detect.py`
- `detect_newline(sample)` — `newline_detect.py`

Each one is exercised independently by the test suite (there is no
higher-level `detect_dialect` wrapper).

## Symptoms

The helpers agree with each other on textbook CSVs — LF newlines, `"`
quotes, `,` delimiter. Anything else is broken:

1. **Quote detection picks non-quote punctuation.** If the sample has
   no `"` or `'` but does contain brackets, `#`, `:` or similar
   characters, `detect_quotechar` returns those instead of the RFC 4180
   default `"`. The legal return values are only `"` and `'`.

2. **Delimiter detection counts inside quoted fields.** For files whose
   quoted fields happen to contain the "wrong" character in bulk (for
   example `"a,b,c";"d,e,f"` — the real separator is `;` but there are
   many `,` inside quotes), the detector picks whatever is most
   frequent globally rather than what actually separates fields.

3. **Newline detection collapses CRLF to LF (or to CR).** For
   CRLF-terminated samples the detector returns `\n` because
   `str.count('\n')` also matches the `\n` inside every `\r\n`, so a
   naive comparison against `sample.count('\r\n')` is always a tie.

## What we need

- All three helpers must return the correct value for the pathological
  samples in `tests/test_bug.py`.
- The existing "clean CSV" tests in `tests/test_core.py` must keep
  passing.
- The three helpers stay independent — no shared top-level orchestrator
  is introduced.
- `stdlib` only. No new dependencies.
