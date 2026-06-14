# バグ: 巻き戻されるべき変更が残ってしまう

`begin(); begin(); set("a", 5); commit(); rollback()` を実行すると `a == 5` が
残りますが、`get("a")` は `None` になるべきです。内側トランザクションをcommitし、
その後に外側をrollbackした場合、その書き込みは完全に破棄されることが期待され
ます。

単一レベルのcommit/rollbackと内側のみのrollbackは既に正しく動作します。
