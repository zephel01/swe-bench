# Bug: values are not escaped for their context (attribute / URL)

Text content is escaped, but other contexts are not:

- Attribute values are escaped with the *text* rules, so a `"` (and payloads
  like `" onerror="alert(1)`) break out of the attribute.
- `href` URLs are emitted unchecked, so `javascript:alert(1)` (in any casing or
  with leading spaces) stays live.

Escape per context: text content, attribute values (also escape `"`/`'`), and
URLs (neutralize dangerous schemes such as `javascript:` to `#`). Plain text and
safe `http(s)` URLs already work.
