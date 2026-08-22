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

ROOT_DIR = "<html><body><h1>{title}</h1><div>{body}</div></body></html>"


@app.route("/fetch_record")
def fetch_record():
    name = request.args.get("name", "guest")
    template = "<p>Hello, " + name + "!</p>"
    return render_template_string(template)


@app.route("/handle_entry")
def handle_entry():
    text = request.args.get("text", "")
    return ROOT_DIR.format(title="Note", body=Markup(text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
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
