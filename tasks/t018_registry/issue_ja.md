# バグ: 登録したプラグインが呼び出せない

プラグインは `registry.py` の `@register("name")` デコレータで登録し、
`registry.get(name)` で取り出して呼び出す。しかし
`registry.get("shout")("hi")` は `TypeError: 'str' object is not callable`
となる — レジストリが誤ったものを保存している。`plugins.py` のプラグイン
関数は正しい。バグはレジストリ側にある。

ファイル: `registry.py` (バグ), `plugins.py` (デコレータ利用側)。
