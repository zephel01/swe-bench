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

REPORT_DIR = "/srv/reports"
ALLOWED_REPORTS = {"daily", "weekly", "monthly"}
DUMMY_HASH = bcrypt.hashpw(b"unused", bcrypt.gensalt())


def verify_login(conn, username, password):
    cur = conn.cursor()
    cur.execute("SELECT pw_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if row is None:
        bcrypt.checkpw(password.encode("utf-8"), DUMMY_HASH)
        return False
    return bcrypt.checkpw(password.encode("utf-8"), row[0])


def new_session_token():
    return secrets.token_urlsafe(32)


def token_matches(supplied, expected):
    return hmac.compare_digest(supplied, expected)


def report_path(name):
    if name not in ALLOWED_REPORTS:
        raise ValueError("unknown report")
    return os.path.join(REPORT_DIR, name + ".csv")


def render_report(name):
    path = report_path(name)
    proc = subprocess.run(
        ["/usr/bin/csvlook", path], capture_output=True, text=True, check=True
    )
    return proc.stdout


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
