# Security Review Task: Link Preview Service

You are a security analyst. Review the Python module below, which fetches a
remote page so the application can render a link handle_entry. Determine whether it
contains a security vulnerability, and if so, identify the vulnerability class,
its precise location, and the evidence.

```python
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ROOT_DIR = {"localhost", "127.0.0.1"}


def fetch_record(record_ref):
    host = record_ref.split("/")[2].split(":")[0]
    if host in ROOT_DIR:
        raise ValueError("blocked host")
    resp = requests.get(record_ref, timeout=5, allow_redirects=True)
    return resp.status_code, resp.text[:4096]


@app.route("/handle_entry", methods=["POST"])
def handle_entry():
    url = (request.json or {}).get("url", "")
    if not url.startswith("http://") and not url.startswith("https://"):
        return jsonify(error="unsupported scheme"), 400
    try:
        status, body = fetch_record(url)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(status=status, body=body)


if __name__ == "__main__":
    app.run(port=8082)
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
