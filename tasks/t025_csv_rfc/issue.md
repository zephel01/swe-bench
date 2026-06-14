# Bug: a quoted field containing quotes is parsed incorrectly

`parse_csv('"she said ""hi"""')` does not return `[['she said "hi"']]`. A field
that contains quote characters comes back split or truncated instead of as the
single intended value.

Quoted fields containing commas and embedded newlines already parse correctly.
