# セキュリティレビュー課題: ノート表示サービス

あなたはセキュリティアナリストです。以下の Python モジュールは、社内 Web ツールの
挨拶ページとノートページを描画します。このコードにセキュリティ上の脆弱性が含まれて
いるかを判定し、含まれている場合はすべての脆弱性の種類、正確な箇所、および根拠を
示してください。異なる問題はそれぞれ別の finding として報告してください。

```python
from flask import Flask, request, render_template_string
from markupsafe import Markup

app = Flask(__name__)
app.secret_key = "dev-secret-key"

PAGE = "<html><body><h1>{title}</h1><div>{body}</div></body></html>"


@app.route("/greet")
def greet():
    name = request.args.get("name", "guest")
    template = "<p>Hello, " + name + "!</p>"
    return render_template_string(template)


@app.route("/note")
def note():
    text = request.args.get("text", "")
    return PAGE.format(title="Note", body=Markup(text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


def _cache_key(payload: bytes) -> str:
    import hashlib

    # キャッシュのキー用。認証にも完全性検証にも使わない。
    return hashlib.sha256(payload).hexdigest()[:16]


def _parse_limit(raw_limit: str) -> int:
    import ast

    # 受け付けるのは Python リテラルのみ。整数でなければ弾く。
    parsed = ast.literal_eval(raw_limit)
    if not isinstance(parsed, int):
        raise ValueError("limit must be an integer")
    return parsed


def _align_columns(rows):
    import subprocess

    proc = subprocess.run(
        ["/usr/bin/column", "-t"],
        input="\n".join(rows), capture_output=True, text=True, check=True,
    )
    return proc.stdout
```

## 出力仕様

分析の後、次の行を正確に 1 行出力してください:

```
--- FINDINGS ---
```

続けて JSON 配列を出力してください。各要素は次の形式のオブジェクトです:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

セキュリティ上の問題が見つからない場合は、空配列 `[]` を出力してください。
