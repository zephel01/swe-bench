# セキュリティレビュー課題: バックアップエンドポイント

あなたはセキュリティアナリストです。以下の Python モジュールは、社内プロジェクト
サーバーのバックアップ用エンドポイントを実装しています。このコードにセキュリティ上の
脆弱性が含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および
根拠を示してください。

```python
import subprocess

from flask import Flask, request, jsonify

app = Flask(__name__)
ARCHIVE_DIR = "/srv/backups"


def create_archive(project_name):
    cmd = f"tar -czf {ARCHIVE_DIR}/{project_name}.tar.gz /srv/projects/{project_name}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def disk_usage(project_name):
    out = subprocess.check_output(
        "du -sh /srv/projects/" + project_name, shell=True, text=True
    )
    return out.split()[0]


@app.route("/backup", methods=["POST"])
def backup():
    project = request.form.get("project", "")
    if not project:
        return jsonify(error="project required"), 400
    code, log = create_archive(project)
    return jsonify(
        status="ok" if code == 0 else "failed",
        size=disk_usage(project),
        log=log,
    )


if __name__ == "__main__":
    app.run(port=8081)


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
