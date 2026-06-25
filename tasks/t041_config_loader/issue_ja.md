# バグ: 環境変数の override が無視されることがある

`CONFIG_DB_PORT=6000` を設定しても `load_config(env)` が既定値 `5432` を返す。
優先順位は全キーで **env > file > defaults** であってほしく、override 値は正しい型
（`db_port` は `int`、`debug` は `bool`）で返るべきで、生の文字列ではない。

`load_config({})` は既定値を正しく返す。無関係な環境変数は今後も無視すること。
