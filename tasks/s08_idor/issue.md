# Security Review Task: Invoice API

You are a security analyst. Review the Python module below, which serves invoice
details to authenticated users of a billing portal. Determine whether it
contains a security vulnerability, and if so, identify the vulnerability class,
its precise location, and the evidence.

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

## Output contract

After your analysis, output a line containing exactly:

```
--- FINDINGS ---
```

Then output a JSON array. Each element must be an object of the form:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

If you find no security issues, output an empty array `[]`.
