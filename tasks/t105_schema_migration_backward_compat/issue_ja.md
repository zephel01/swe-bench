# `User.name` を `first_name` / `last_name` に分割（後方互換つき）

## 課題

現状 `User` は `name: str` の 1 フィールドだけを持つ。これを `first_name` と
`last_name` の 2 フィールドに分割したい。ただし既存コードと既存データを壊しては
ならない：

- 既存呼び出しは `save_user(user, path)` と `load_user(path)` を使っている。
  シグネチャは変えない。
- ディスク上の永続 JSON は旧形式 `{"name": "Alice Wonder"}` で書かれている。
  `load_user` はこれを透過的にマイグレーションして読める必要がある。
- 新しい書き込みは新形式 `{"first_name": ..., "last_name": ...}` を出力し、
  `load_user` はこの形式も読める。
- 旧コードは今後も `user.name` でアクセスする。`User` は `first_name` と
  `last_name` を結合した `name` プロパティを提供すること（前後空白は trim）。
- `migrate_legacy(record: dict) -> dict` を公開関数として提供する。

## 受け入れ条件

- `User` は dataclass。`first_name: str` と `last_name: str` を持ち、両者を
  連結する `name` プロパティを持つ。
- `save_user(user, path)` は新スキーマだけを書き出す。
- `load_user(path)` はどちらのスキーマも受け付ける。旧スキーマなら
  `migrate_legacy` を通してから `User` を構築する。
- `migrate_legacy({"name": "Alice Wonder"})` は
  `{"first_name": "Alice", "last_name": "Wonder"}` を返す。
- 単語 1 個の旧 name は `first_name=<name>, last_name=""` に分ける。
- 既に新スキーマのレコードは `migrate_legacy` を通しても不変。
