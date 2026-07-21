# リファクタ: `User` の identifier 型を `str` に統一する

`User` の identifier 型が user モジュールの 4 ファイル
(`model.py`, `repo.py`, `service.py`, `api.py`) で不統一になっており、
同一ユーザが別々のキーで保存され、`get` / `exists` が静かに壊れる。

## 現状

- `model.User.id` の型注釈が `int`。
- `repo.UserRepo` は `int` キーで保存し、`get` / `exists` の注釈も `int`。
- `service.UserService` の各メソッドは `id` パラメータに型注釈がない。
- `api.API.create` は `payload["id"]` をそのまま下流に流している。
  現実のクライアントは `int` も `str` も送ってくるため、同じユーザが
  `1`(int) と `"1"`(str) 両方のキーで保存され、後続の `get` / `exists` が
  型ミスマッチで黙って外れる。

## あるべき姿

内部 identifier を `str` (UUID 相当) に統一する:

- `User.id: str`。
- `UserRepo.save` / `get` / `exists` は `str` id を要求、`str` キーで保存。
  非 `str` id は境界で `TypeError` (明示的な `isinstance` 検査)。
- `UserService.register` / `find` / `is_registered` は `id: str` と宣言。
- `api.API` は既存クライアント互換のため、入口 (`create` は `payload["id"]`
  経由、`get` は直接) で `int` と `str` の両方を受け付け、**内部で `str(id)`
  に正規化してから** service を呼ぶ。`API.get` の `id` の型注釈は
  `Union[int, str]` (`int | str`) とする。

**1〜3 ファイルだけの修正では通らない**: `test_bug.py` か
`test_consistency.py` のどちらかが必ず赤のまま残るので、4 ファイル
すべてを整合させて修正すること。
