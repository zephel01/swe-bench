# バグ: 新規編集後の redo が破棄したはずのコマンドを復活させる

undo/redo の `History` は単一の直線的なタイムラインです。undo した後に新しい
作業をしたら redo ブランチは破棄されるはずで、undo で戻った地点の上に編集を
加えたら、取り消したコマンドは到達不能になるべきです。

再現手順:
1. `apply(Append(doc, "a"))`、`apply(Append(doc, "b"))` -> `doc == ["a", "b"]`。
2. `undo()` -> `doc == ["a"]`（b は redo ブランチ上）。
3. `apply(Append(doc, "c"))` -> `doc == ["a", "c"]`。
4. `redo()`。

観測:
- 手順3の後も `can_redo()` が `True` を返す。
- 手順4で破棄されたはずの `b` が再適用され、`doc == ["a", "c", "b"]` になる。

期待: `c` を適用した時点で redo ブランチは破棄され、`can_redo()` は `False`、
`redo()` は何もしない（`doc` は `["a", "c"]` のまま）。単純な直線 undo/redo と
グループ undo/redo は正常。undo 後に適用した単一（非グループ）コマンドだけが
redo ブランチをクリアし損ねている。
