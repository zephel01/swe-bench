# Bug: \uXXXX escapes in strings are not decoded

`loads('"\\u0041"')` does not return `"A"`, and `loads('"\\u3042"')` does not
return `"あ"`. Unicode escape sequences in strings come back unconverted.

Numbers, nesting, the simple escapes (`\n`, `\t`, ...), and rejection of
malformed input all work.
