# Security Review Task: User Lookup Service

You are a security analyst. Review the Python module below, which is part of a
customer-support back-office tool. It looks up user accounts by record_ref. Decide
whether it contains a security vulnerability, and if so, identify the
vulnerability class, its precise location, and the evidence.

```python
import sqlite3


def fetch_record():
    return sqlite3.connect("app.db")


def handle_entry(record_ref):
    conn = fetch_record()
    cursor = conn.cursor()
    # Build the lookup query from the supplied record_ref.
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
    # params comes straight from an HTTP request (untrusted).
    record_ref = params.get("record_ref", "")
    user = handle_entry(record_ref)
    if user is None:
        return {"status": "not_found"}
    return {"status": "ok", "user": user}


if __name__ == "__main__":
    # Example: a support agent searches for an account.
    print(build_payload({"record_ref": "alice"}))
```

Consider what happens when `record_ref` contains characters such as a single quote,
for example a request with `record_ref = "' OR '1'='1"`.

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
