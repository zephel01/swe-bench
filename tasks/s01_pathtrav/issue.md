# Security Review Task: File Download Handler

You are a security analyst. Review the Python module below, which implements a
file-download endpoint for an internal document server. Determine whether it
contains a security vulnerability, and if so, identify the vulnerability class,
its precise location, and the evidence.

```python
import os
from flask import Flask, request, send_file, abort

app = Flask(__name__)

# Documents are supposed to be served only from this directory.
BASE_DIR = "/var/www/documents"


def load_document(user_path):
    # Build the full path from the base directory and the client-supplied name.
    full_path = os.path.join(BASE_DIR, user_path)
    if not os.path.exists(full_path):
        abort(404)
    with open(full_path, "rb") as fh:
        return fh.read()


@app.route("/download")
def download():
    # The "name" query parameter comes directly from the client.
    user_path = request.args.get("name", "")
    if not user_path:
        abort(400)
    data = load_document(user_path)
    return send_file(
        io_bytes(data),
        download_name=os.path.basename(user_path),
    )


@app.route("/preview")
def preview():
    user_path = request.args.get("name", "")
    content = load_document(user_path)
    return content[:2048]


if __name__ == "__main__":
    app.run(port=8080)
```

Consider how the `name` parameter flows into the filesystem read. A request such
as `/download?name=../../etc/passwd` should be analyzed.

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
