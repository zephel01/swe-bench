# バグ: config のレイヤ優先順位が誤り (env と file)

`load_config(env, file_config)` は3つのソースを重ねる。意図する優先順位は全キーで
**env > file > defaults** で、override 値は宣言型に変換する（`db_port` は `int`、
`debug` は `bool`）。

観測: 同じキーが設定ファイルと環境変数の両方にあると **file 値が勝ってしまう**。
例: `CONFIG_DB_PORT=6000` と file `{"db_port": 7000}` で `7000` が返るが、`6000` が
正しい。env のみの override と file のみの値は動作し、残りは defaults で埋まる。
