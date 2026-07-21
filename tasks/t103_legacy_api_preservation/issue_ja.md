# search() のシグネチャ移行

旧クライアントコードが `search(q, filters)` を至る所で呼んでいる。既存の
呼び出し箇所を壊さずに、新しく `search(SearchRequest)` 形式を追加したい。

要件:

- `search("python")` と `search("python", {"category": "book"})` は
  これまで通りの結果を返し続けること（例外を出さない）。
- 新しく `search(SearchRequest(q=..., filters=..., limit=..., offset=...))`
  形式も動作し、新規コードではこちらを推奨とする。
- 内部実装は1本化し、両APIから同じ処理に委譲すること。
- 旧APIの呼び出しでは `DeprecationWarning`（専用の
  `LegacySearchDeprecated` サブクラス）を発行して、移行状況を追跡できる
  ようにすること。
- `SearchRequest`, `search`, `LegacySearchDeprecated` はパッケージから
  公開（`__all__`）すること。

`tests/` 配下のテストが全て通るようにコードを拡張してください。
