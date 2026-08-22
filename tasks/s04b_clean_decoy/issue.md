# Security Review Task: Configuration Loader

You are a security analyst. Review the Python module below, which loads a named
configuration file from a fixed directory and looks up a setting in a database.
Decide whether it contains a real security vulnerability. Only report genuine,
demonstrable issues — do not flag safe, idiomatic code.

```python
import os
import sqlite3

CONFIG_DIR = "/etc/myapp/configs"
ALLOWED = {"prod", "staging", "dev"}


def load_config(name):
    # Only a fixed set of names is accepted; anything else is rejected.
    if name not in ALLOWED:
        raise ValueError("unknown config name")
    full_path = os.path.join(CONFIG_DIR, name + ".conf")
    # Defense in depth: ensure the resolved path stays inside CONFIG_DIR.
    real = os.path.realpath(full_path)
    if not real.startswith(CONFIG_DIR + os.sep):
        raise ValueError("path escapes config directory")
    with open(real, "r", encoding="utf-8") as fh:
        return fh.read()


def get_setting(conn, key):
    cursor = conn.cursor()
    # Parameterized query: the key is bound, never concatenated.
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def main():
    env = os.environ.get("APP_ENV", "dev")
    text = load_config(env)
    conn = sqlite3.connect("settings.db")
    try:
        timeout = get_setting(conn, "timeout")
    finally:
        conn.close()
    print(text, timeout)


if __name__ == "__main__":
    main()


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
