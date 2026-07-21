# 既存呼び出しを壊さずに `parse()` へ `strict` モードを追加する

## 背景

設定パーサは単一のエントリポイントを公開している:

```python
from parser import parse

parse(text)
```

書式は行指向で単純:

- `KEY=VALUE` — 代入 (`=` 前後の空白は除去)
- `@unset KEY` — キー削除
- `#` で始まる行と空行は無視
- それ以外の行は静かに無視、キー重複は後勝ちで上書き

多くの本番コードがこの緩い挙動に依存している。

## 要件

`parse` に `strict: bool = False` というキーワード引数を追加する。

- `strict=False`(既定)は現状と**完全に同じ**挙動でなければならない。
  既存の呼び出し(`strict` を指定しないもの)は 1 件も壊れてはならない。
- `strict=True` の場合は**個別**の例外を送出する:
  - `DuplicateKeyError` — 同じキーが複数回代入されたとき
  - `UnknownDirectiveError` — 未知の `@directive` が現れたとき
  - `SyntaxError` — コメント/空行/ディレクティブ/`KEY=VALUE` のいずれでもない行

3 つの個別例外はすべて `ParseError` を継承していること。`exceptions`
モジュールから `ParseError`, `SyntaxError`, `DuplicateKeyError`,
`UnknownDirectiveError` を公開する。

## 受け入れ基準

1. 既存の呼び出し(`strict` 未指定)がすべて動作すること。
2. `parse(text, strict=True)` は原因ごとに専用サブクラスを投げること
   (すべてを汎用 `ParseError` にまとめる実装は不合格)。
3. 個別例外はすべて `ParseError` を継承していること。
