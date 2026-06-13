# Bug: trie reports prefixes as stored words

After `t.insert("apple")`, calling `t.search("app")` returns `True`, but
`"app"` was never inserted as a word — only as a prefix of `"apple"`.
`search` must return `True` only for whole words that were inserted, while
`starts_with` keeps matching prefixes. Inserting `"app"` afterwards should
then make `search("app")` return `True`.

File: `trie.py`.
