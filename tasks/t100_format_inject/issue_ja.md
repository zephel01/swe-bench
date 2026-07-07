# バグ: テンプレートレンダラがフォーマットフィールド経由でオブジェクト内部を露出する

`safe_format(template, *args, **kwargs)` は、呼び出し側が渡した値に対して、
ユーザー提供の `template` を描画します。これは単純な名前付き／位置フィールドの
置換のみを意図しています。ところが、テンプレートが置換対象の値の内部に到達
できてしまいます。

報告されている問題（描画せず `ValueError` を送出すべき）:

- `safe_format("{x.__class__}", x=1)` が `x` の型を露出する。
- `safe_format("{0.__class__.__init__.__globals__}", object())` がモジュールの
  グローバルに到達する。
- `safe_format("{conf[secret]}", conf={"secret": "s3cr3t"})` が渡された
  オブジェクトへ添字アクセスする。

通常のテンプレートは引き続き動作しなければなりません:

- `safe_format("{name} is {age}", name="Bob", age=42)` -> `"Bob is 42"`
- `safe_format("{0}-{1}", "a", "b")` -> `"a-b"`
- `safe_format("{{literal}}")` -> `"{literal}"`
- `safe_format("{0:>5}", "hi")` -> `"   hi"`、`safe_format("{0!r}", "hi")`
  -> `"'hi'"`
