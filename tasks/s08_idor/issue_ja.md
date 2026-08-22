# セキュリティレビュー課題: 請求書 API

あなたはセキュリティアナリストです。以下の Python モジュールは、請求ポータルの
認証済みユーザーに請求書の詳細を返します。このコードにセキュリティ上の脆弱性が
含まれているかを判定し、含まれている場合は脆弱性の種類、正確な箇所、および根拠を
示してください。

```python
import os
import sqlite3
from functools import wraps

from flask import Flask, session, jsonify, abort

app = Flask(__name__)
app.secret_key = os.environ["APP_SECRET"]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            abort(401)
        return fn(*args, **kwargs)
    return wrapper


def get_invoice(conn, invoice_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, owner_id, amount, pdf_path FROM invoices WHERE id = ?",
        (invoice_id,),
    )
    return cur.fetchone()


@app.route("/api/invoices/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    conn = sqlite3.connect("billing.db")
    try:
        row = get_invoice(conn, invoice_id)
    finally:
        conn.close()
    if row is None:
        abort(404)
    return jsonify(id=row[0], amount=row[2], pdf=row[3])
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
