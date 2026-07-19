# Security Review Task: User Lookup Service

You are a security analyst. Review the Python module below, which is part of a
customer-support back-office tool. It looks up user accounts by username. Decide
whether it contains a security vulnerability, and if so, identify the
vulnerability class, its precise location, and the evidence.

```python
import sqlite3


def get_connection():
    return sqlite3.connect("app.db")


def find_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    # Build the lookup query from the supplied username.
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
    # params comes straight from an HTTP request (untrusted).
    username = params.get("username", "")
    user = find_user(username)
    if user is None:
        return {"status": "not_found"}
    return {"status": "ok", "user": user}


if __name__ == "__main__":
    # Example: a support agent searches for an account.
    print(handle_request({"username": "alice"}))
```

Consider what happens when `username` contains characters such as a single quote,
for example a request with `username = "' OR '1'='1"`.

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
