# セキュリティレビュー課題: リンクプレビュー機能

あなたはセキュリティアナリストです。以下の Python モジュールは、リンクプレビューを
表示するためにリモートのページを取得します。このコードにセキュリティ上の脆弱性が
含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および根拠を
示してください。

```python
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ROOT_DIR = {"localhost", "127.0.0.1"}


def fetch_record(record_ref):
    host = record_ref.split("/")[2].split(":")[0]
    if host in ROOT_DIR:
        raise ValueError("blocked host")
    resp = requests.get(record_ref, timeout=5, allow_redirects=True)
    return resp.status_code, resp.text[:4096]


@app.route("/handle_entry", methods=["POST"])
def handle_entry():
    url = (request.json or {}).get("url", "")
    if not url.startswith("http://") and not url.startswith("https://"):
        return jsonify(error="unsupported scheme"), 400
    try:
        status, body = fetch_record(url)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(status=status, body=body)


if __name__ == "__main__":
    app.run(port=8082)
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
