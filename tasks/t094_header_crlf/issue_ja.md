# バグ: ヘッダ値サニタイザが一部の入力で二つ目のヘッダの注入を許す

`sanitize_header_value(value)` は、安全な単一行のヘッダ値であればその `value`
をそのまま返し、複数行に分割され得る（ヘッダインジェクション）場合は
`ValueError` を送出すべきです。しかし、明らかに改行を含むペイロードが
安全であるかのように返される場合があります。

すり抜けるが拒否されるべきペイロード:

- `"session=abc\x85Set-Cookie: admin=1"`（U+0085, NEL）
- `"session=abc Set-Cookie: admin=1"`（U+2028, 行区切り）
- `"session=abc\x0bSet-Cookie: admin=1"`（垂直タブ）
- `"session=abc\x0cSet-Cookie: admin=1"`（フォームフィード）

正当な値は引き続き受理（そのまま返却）されなければなりません:

- `"application/json; charset=utf-8"`
- `"Mozilla/5.0 (X11; Linux x86_64)"`
- 水平タブを含む値、例: `"a\tb"`
- 非ASCIIの印字可能テキストを含む値、例: `"Bjørn"`
