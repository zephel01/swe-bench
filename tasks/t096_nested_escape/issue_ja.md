# バグ: 検索リンクがURLとHTMLの入れ子コンテキストでクエリを誤ってエンコードする

`render_search_link(query, label)` は `/search?q=<query>` を指し、`<label>` を
表示するアンカーを構築します。クエリ値は同時に2つの入れ子コンテキストに置かれ
ます。すなわちURLのクエリ構成要素であり、それ自体がHTML属性の内側にあります。
値が単一の不透明なクエリパラメータのまま残り、リンクを改変できないように、
両方のエンコードを適用しなければなりません。

報告されている問題:

- `render_search_link("a&b=c", "x")` は、`a`, `b`, `c` が1つの値ではなく別々の
  クエリパラメータのように見える `href` を生成する。
- `render_search_link("a#frag", "x")` は、`#` 以降がクエリから落ちてフラグメント
  になる `href` を生成する。

通常の入力はそのまま動作しなければなりません:

- `render_search_link("hello", "Home")` は
  `<a href="/search?q=hello">Home</a>` を返す。
- `render_search_link("abc123", "x")` は `q=abc123` を保つ（安全な文字を不必要に
  書き換えない）。
