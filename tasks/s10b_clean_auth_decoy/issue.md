# Security Review Task: Login and Report Helpers

You are a security analyst. Review the Python module below, which handles
password verification, session tokens, and CSV report rendering. Decide whether
it contains a real security vulnerability. Only report genuine, demonstrable
issues — do not flag safe, idiomatic code.

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

    # Cache key only; never used for authentication or integrity.
    return hashlib.sha256(payload).hexdigest()[:16]


def _parse_limit(raw_limit: str) -> int:
    import ast

    # Only Python literals are accepted; non-integers are rejected.
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
