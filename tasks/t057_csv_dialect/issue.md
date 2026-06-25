# Bug: CSV parser assumes commas and ignores quoting

`parse(text)` is hard-wired to comma and splits naively, so it fails on files
that use `;` or tab delimiters and on quoted fields. From these examples it
should auto-detect the delimiter and respect RFC4180 quoting:

- `"a;b;c\n1;2;3"` → delimiter `;`.
- A field like `"Smith, Jr."` must stay one field even though it contains the
  delimiter.
- A quoted field may contain a newline.

Standard comma CSV already parses.
