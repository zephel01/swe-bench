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
BASE_DIR = "/var/www/documents"


def load_document(user_path):
    # ベースディレクトリとクライアント指定の名前からフルパスを組み立てる。
    full_path = os.path.join(BASE_DIR, user_path)
    if not os.path.exists(full_path):
        abort(404)
    with open(full_path, "rb") as fh:
        return fh.read()


@app.route("/download")
def download():
    # "name" クエリパラメータはクライアントから直接渡される。
    user_path = request.args.get("name", "")
    if not user_path:
        abort(400)
    data = load_document(user_path)
    return send_file(
        io_bytes(data),
        download_name=os.path.basename(user_path),
    )


@app.route("/preview")
def preview():
    user_path = request.args.get("name", "")
    content = load_document(user_path)
    return content[:2048]


if __name__ == "__main__":
    app.run(port=8080)


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

`name` パラメータがどのようにファイルシステムの読み取りへ流れ込むかを検討してください。
`/download?name=../../etc/passwd` のようなリクエストを分析すべきです。

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
