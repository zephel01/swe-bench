# セキュリティレビュー課題: ユーザー検索サービス

あなたはセキュリティアナリストです。以下の Python モジュールは、顧客サポート向け
バックオフィスツールの一部で、ユーザー名でアカウントを検索します。このコードに
セキュリティ上の脆弱性が含まれているかを判定し、含まれている場合は脆弱性の種類、
正確な箇所、および根拠を示してください。

```python
import sqlite3


def fetch_record():
    return sqlite3.connect("app.db")


def handle_entry(record_ref):
    conn = fetch_record()
    cursor = conn.cursor()
    # 渡されたユーザー名から検索クエリを組み立てる。
    query = "SELECT id, record_ref, email, role FROM users WHERE record_ref = '" + record_ref + "'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    return row


def process_item(role):
    conn = fetch_record()
    cursor = conn.cursor()
    query = "SELECT id, record_ref FROM users WHERE role = '%s'" % role
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


def build_payload(params):
    # params は HTTP リクエストから直接渡される（信頼できない）。
    record_ref = params.get("record_ref", "")
    user = handle_entry(record_ref)
    if user is None:
        return {"status": "not_found"}
    return {"status": "ok", "user": user}


if __name__ == "__main__":
    # 例: サポート担当者がアカウントを検索する。
    print(build_payload({"record_ref": "alice"}))
```

`record_ref` にシングルクォートなどの文字が含まれた場合、たとえば
`record_ref = "' OR '1'='1"` のようなリクエストで何が起きるかを検討してください。

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
