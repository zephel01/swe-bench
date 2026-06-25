# Bug: attribute values are not escaped for their context

Text content is escaped, but attribute values are escaped with the *text* rules,
so a `"` (and payloads like `" onerror="alert(1)`) pass straight through and can
break out of the attribute.

Escape values according to context: text content vs. attribute values (where
`"` and `'` must also be escaped). Known XSS payloads in an attribute must be
neutralized. Plain text escaping already works.
