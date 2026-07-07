# Bug: header value sanitizer lets some inputs inject a second header

`sanitize_header_value(value)` should return `value` unchanged when it is a
safe single-line header value, and raise `ValueError` when the value could be
split into more than one line (header injection). Some payloads that clearly
carry a line break are returned as if they were safe.

Payloads that leak through but must be rejected:

- `"session=abc\x85Set-Cookie: admin=1"` (U+0085, NEL).
- `"session=abc Set-Cookie: admin=1"` (U+2028, line separator).
- `"session=abc\x0bSet-Cookie: admin=1"` (vertical tab).
- `"session=abc\x0cSet-Cookie: admin=1"` (form feed).

Legitimate values must still be accepted (returned unchanged), including:

- `"application/json; charset=utf-8"`.
- `"Mozilla/5.0 (X11; Linux x86_64)"`.
- A value containing a horizontal tab, e.g. `"a\tb"`.
- A value with non-ASCII printable text, e.g. `"Bjørn"`.
