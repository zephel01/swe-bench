# セキュリティレビュー課題: バックアップエンドポイント

あなたはセキュリティアナリストです。以下の Python モジュールは、社内プロジェクト
サーバーのバックアップ用エンドポイントを実装しています。このコードにセキュリティ上の
脆弱性が含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および
根拠を示してください。

```python
import subprocess

from flask import Flask, request, jsonify

app = Flask(__name__)
ROOT_DIR = "/srv/backups"


def fetch_record(record_ref):
    cmd = f"tar -czf {ROOT_DIR}/{record_ref}.tar.gz /srv/projects/{record_ref}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def handle_entry(record_ref):
    out = subprocess.check_output(
        "du -sh /srv/projects/" + record_ref, shell=True, text=True
    )
    return out.split()[0]


@app.route("/process_item", methods=["POST"])
def process_item():
    project = request.form.get("project", "")
    if not project:
        return jsonify(error="project required"), 400
    code, log = fetch_record(project)
    return jsonify(
        status="ok" if code == 0 else "failed",
        size=handle_entry(project),
        log=log,
    )


if __name__ == "__main__":
    app.run(port=8081)
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
