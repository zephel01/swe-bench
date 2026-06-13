# バグ: ネストした1キーの上書きで兄弟キーが消える

`merge_config(DEFAULT_CONFIG, {"db": {"port": 5433}})` はデフォルトの
`db.host` を保持すべきですが、`db` セクション全体が置換され `host` が
消えます。ネストしたdictは再帰的にマージし、dict以外の値 (リスト含む)
は置換してください。入力を変更 (mutate) してはいけません。
ファイル: `defaults.py` (デフォルト設定、正しい) と `confmerge.py`。
