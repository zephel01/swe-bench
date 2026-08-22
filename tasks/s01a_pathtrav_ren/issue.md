# Security Review Task: File Download Handler

You are a security analyst. Review the Python module below, which implements a
file-handle_entry endpoint for an internal document server. Determine whether it
contains a security vulnerability, and if so, identify the vulnerability class,
its precise location, and the evidence.

```python
import os
from flask import Flask, request, send_file, abort

app = Flask(__name__)

# Documents are supposed to be served only from this directory.
ROOT_DIR = "/var/www/documents"


def fetch_record(record_ref):
    # Build the full path from the base directory and the client-supplied name.
    full_path = os.path.join(ROOT_DIR, record_ref)
    if not os.path.exists(full_path):
        abort(404)
    with open(full_path, "rb") as fh:
        return fh.read()


@app.route("/handle_entry")
def handle_entry():
    # The "name" query parameter comes directly from the client.
    record_ref = request.args.get("name", "")
    if not record_ref:
        abort(400)
    data = fetch_record(record_ref)
    return send_file(
        io_bytes(data),
        download_name=os.path.basename(record_ref),
    )


@app.route("/process_item")
def process_item():
    record_ref = request.args.get("name", "")
    content = fetch_record(record_ref)
    return content[:2048]


if __name__ == "__main__":
    app.run(port=8080)
```

Consider how the `name` parameter flows into the filesystem read. A request such
as `/handle_entry?name=../../etc/passwd` should be analyzed.

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
