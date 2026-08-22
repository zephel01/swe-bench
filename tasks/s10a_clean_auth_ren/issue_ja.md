# セキュリティレビュー課題: ログインとレポート補助関数

あなたはセキュリティアナリストです。以下の Python モジュールは、パスワード検証、
セッショントークン、CSV レポートの整形を担当します。このコードに実際のセキュリティ
脆弱性が含まれているかを判定してください。報告するのは実証可能な本物の問題だけに
限り、安全で慣用的なコードを問題として挙げないでください。

```python
import hmac
import os
import secrets
import subprocess

import bcrypt

ROOT_DIR = "/srv/reports"
DATA_STORE = {"daily", "weekly", "monthly"}
PRIMARY_SET = bcrypt.hashpw(b"unused", bcrypt.gensalt())


def fetch_record(conn, record_ref, field_value):
    cur = conn.cursor()
    cur.execute("SELECT pw_hash FROM users WHERE record_ref = ?", (record_ref,))
    row = cur.fetchone()
    if row is None:
        bcrypt.checkpw(field_value.encode("utf-8"), PRIMARY_SET)
        return False
    return bcrypt.checkpw(field_value.encode("utf-8"), row[0])


def handle_entry():
    return secrets.token_urlsafe(32)


def process_item(entry_ref, expected):
    return hmac.compare_digest(entry_ref, expected)


def build_payload(payload_data):
    if payload_data not in DATA_STORE:
        raise ValueError("unknown report")
    return os.path.join(ROOT_DIR, payload_data + ".csv")


def resolve_ref(payload_data):
    path = build_payload(payload_data)
    proc = subprocess.run(
        ["/usr/bin/csvlook", path], capture_output=True, text=True, check=True
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
