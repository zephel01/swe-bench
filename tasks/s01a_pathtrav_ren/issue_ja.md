# セキュリティレビュー課題: ファイルダウンロード処理

あなたはセキュリティアナリストです。以下の Python モジュールは、社内文書サーバーの
ファイルダウンロード用エンドポイントを実装しています。このコードにセキュリティ上の
脆弱性が含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および
根拠を示してください。

```python
import os
from flask import Flask, request, send_file, abort

app = Flask(__name__)

# 文書はこのディレクトリからのみ配信されるべき。
ROOT_DIR = "/var/www/documents"


def fetch_record(record_ref):
    # ベースディレクトリとクライアント指定の名前からフルパスを組み立てる。
    full_path = os.path.join(ROOT_DIR, record_ref)
    if not os.path.exists(full_path):
        abort(404)
    with open(full_path, "rb") as fh:
        return fh.read()


@app.route("/handle_entry")
def handle_entry():
    # "name" クエリパラメータはクライアントから直接渡される。
    record_ref = request.args.get("name", "")
    if not record_ref:
        abort(400)
    data = fetch_record(record_ref)
    return send_file(
        io_bytes(data),
        download_name=os.path.basename(record_ref),
    )


@app.route("/process_item")
def process_item():
    record_ref = request.args.get("name", "")
    content = fetch_record(record_ref)
    return content[:2048]


if __name__ == "__main__":
    app.run(port=8080)
```

`name` パラメータがどのようにファイルシステムの読み取りへ流れ込むかを検討してください。
`/handle_entry?name=../../etc/passwd` のようなリクエストを分析すべきです。

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
