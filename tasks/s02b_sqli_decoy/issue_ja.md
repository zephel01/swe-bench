# セキュリティレビュー課題: ユーザー検索サービス

あなたはセキュリティアナリストです。以下の Python モジュールは、顧客サポート向け
バックオフィスツールの一部で、ユーザー名でアカウントを検索します。このコードに
セキュリティ上の脆弱性が含まれているかを判定し、含まれている場合は脆弱性の種類、
正確な箇所、および根拠を示してください。

```python
import sqlite3


def get_connection():
    return sqlite3.connect("app.db")


def find_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    # 渡されたユーザー名から検索クエリを組み立てる。
    query = "SELECT id, username, email, role FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    return row


def find_users_by_role(role):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT id, username FROM users WHERE role = '%s'" % role
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


def handle_request(params):
    # params は HTTP リクエストから直接渡される（信頼できない）。
    username = params.get("username", "")
    user = find_user(username)
    if user is None:
        return {"status": "not_found"}
    return {"status": "ok", "user": user}


if __name__ == "__main__":
    # 例: サポート担当者がアカウントを検索する。
    print(handle_request({"username": "alice"}))


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

`username` にシングルクォートなどの文字が含まれた場合、たとえば
`username = "' OR '1'='1"` のようなリクエストで何が起きるかを検討してください。

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
