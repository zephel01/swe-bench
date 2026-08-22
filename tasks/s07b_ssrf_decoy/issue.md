# Security Review Task: Link Preview Service

You are a security analyst. Review the Python module below, which fetches a
remote page so the application can render a link preview. Determine whether it
contains a security vulnerability, and if so, identify the vulnerability class,
its precise location, and the evidence.

```python
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BLOCKED_HOSTS = {"localhost", "127.0.0.1"}


def fetch_preview(target_url):
    host = target_url.split("/")[2].split(":")[0]
    if host in BLOCKED_HOSTS:
        raise ValueError("blocked host")
    resp = requests.get(target_url, timeout=5, allow_redirects=True)
    return resp.status_code, resp.text[:4096]


@app.route("/preview", methods=["POST"])
def preview():
    url = (request.json or {}).get("url", "")
    if not url.startswith("http://") and not url.startswith("https://"):
        return jsonify(error="unsupported scheme"), 400
    try:
        status, body = fetch_preview(url)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(status=status, body=body)


if __name__ == "__main__":
    app.run(port=8082)


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
