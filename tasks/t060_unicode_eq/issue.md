# Bug: visually identical strings compare as different

`equal(a, b)` does a raw codepoint comparison, so a precomposed `é` (`é`)
and a decomposed `é` (`e` + combining acute) come back as not equal even though
they are the same text. Case folding via `fold=True` also fails for non-ASCII
(e.g. `"straße"` vs `"STRASSE"`).

Normalize (NFC) before comparing, and use proper Unicode case folding when
`fold=True`. Plain ASCII comparison already works.
