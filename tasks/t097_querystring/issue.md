# Bug: query-string parser mangles "+", percent escapes and duplicate keys

`parse_query(qs)` should parse an URL-encoded query string into a mapping from
each key to the **list** of values seen for it (values in order). Decoding must
follow the rules for a query component.

Reported problems:

- `parse_query("a=1&a=2")` loses the first value; the repeated key should map
  to `["1", "2"]`.
- `parse_query("q=a+b")` keeps a literal `+`; in a query component `+` means a
  space, so the value should be `"a b"`.
- `parse_query("q=a%2Bb")` should decode to a literal `+` (`"a+b"`), not stay
  `"a%2Bb"`.

Inputs that already work must keep working:

- `parse_query("a=1&b=2")` -> `{"a": ["1"], "b": ["2"]}`.
- `parse_query("q=hello%20world")` -> `{"q": ["hello world"]}`.
- `parse_query("flag")` -> `{"flag": [""]}`.
- `parse_query("x=100%")` keeps the trailing `%` literally -> `{"x": ["100%"]}`.
