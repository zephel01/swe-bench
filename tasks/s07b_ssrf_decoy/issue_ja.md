# セキュリティレビュー課題: リンクプレビュー機能

あなたはセキュリティアナリストです。以下の Python モジュールは、リンクプレビューを
表示するためにリモートのページを取得します。このコードにセキュリティ上の脆弱性が
含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および根拠を
示してください。

```python
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BLOCKED_HOSTS = {"localhost", "127.0.0.1"}


def fetch_preview(target_url):
    host = target_url.split("/")[2].split(":")[0]
    if host in BLOCKED_HOSTS:
        raise ValueError("blocked host")
    resp = requests.get(target_url, timeout=5, allow_redirects=True)
    return resp.status_code, resp.text[:4096]


@app.route("/preview", methods=["POST"])
def preview():
    url = (request.json or {}).get("url", "")
    if not url.startswith("http://") and not url.startswith("https://"):
        return jsonify(error="unsupported scheme"), 400
    try:
        status, body = fetch_preview(url)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(status=status, body=body)


if __name__ == "__main__":
    app.run(port=8082)


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
