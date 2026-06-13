# バグ: トライ木が接頭辞を単語として誤判定する

`t.insert("apple")` の後、`t.search("app")` が `True` を返すが、`"app"`
は単語として挿入されておらず `"apple"` の接頭辞にすぎない。`search` は
挿入された「単語そのもの」にのみ `True` を返すべきで、`starts_with` は
接頭辞一致を維持する。あとから `"app"` を挿入すれば `search("app")` は
`True` になるべき。

ファイル: `trie.py`。
