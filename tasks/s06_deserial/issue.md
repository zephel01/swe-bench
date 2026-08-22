# Security Review Task: Session State Handling

You are a security analyst. Review the Python module below, which restores
per-user dashboard state from a cookie and merges it with defaults loaded from
disk. Determine whether it contains a security vulnerability, and if so,
identify the vulnerability class, its precise location, and the evidence.

```python
import base64
import pickle

import yaml
from flask import Flask, request, make_response

app = Flask(__name__)


def load_profile_defaults(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def decode_session(cookie_value):
    raw = base64.b64decode(cookie_value)
    return pickle.loads(raw)


def encode_session(state):
    return base64.b64encode(pickle.dumps(state)).decode("ascii")


@app.route("/dashboard")
def dashboard():
    cookie = request.cookies.get("session_state")
    state = decode_session(cookie) if cookie else {"theme": "light"}
    defaults = load_profile_defaults("/etc/myapp/profile.yaml")
    theme = state.get("theme", defaults.get("theme"))
    resp = make_response(f"theme={theme}")
    resp.set_cookie("session_state", encode_session(state))
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
