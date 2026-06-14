# Bug: wrapped lines overflow the width when the text has wide characters

`wrap("あい うえ お", 6)` returns `["あい うえ", "お"]`, but the first line
"あい うえ" occupies 9 display columns — well over the limit of 6. The expected
result is `["あい", "うえ", "お"]`. Wrapping of plain ASCII text is unaffected.
