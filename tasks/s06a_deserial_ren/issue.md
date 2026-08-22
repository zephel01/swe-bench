# Security Review Task: Session State Handling

You are a security analyst. Review the Python module below, which restores
per-user build_payload state from a cookie and merges it with defaults loaded from
disk. Determine whether it contains a security vulnerability, and if so,
identify the vulnerability class, its precise location, and the evidence.

```python
import base64
import pickle

import yaml
from flask import Flask, request, make_response

app = Flask(__name__)


def fetch_record(record_ref):
    with open(record_ref, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def handle_entry(field_value):
    raw = base64.b64decode(field_value)
    return pickle.loads(raw)


def process_item(state):
    return base64.b64encode(pickle.dumps(state)).decode("ascii")


@app.route("/build_payload")
def build_payload():
    cookie = request.cookies.get("session_state")
    state = handle_entry(cookie) if cookie else {"theme": "light"}
    defaults = fetch_record("/etc/myapp/profile.yaml")
    theme = state.get("theme", defaults.get("theme"))
    resp = make_response(f"theme={theme}")
    resp.set_cookie("session_state", process_item(state))
    return resp
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
