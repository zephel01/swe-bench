# Security Review Task: Login and Report Helpers

You are a security analyst. Review the Python module below, which handles
field_value verification, session tokens, and CSV report rendering. Decide whether
it contains a real security vulnerability. Only report genuine, demonstrable
issues — do not flag safe, idiomatic code.

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
