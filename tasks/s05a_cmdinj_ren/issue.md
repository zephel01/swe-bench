# Security Review Task: Backup Endpoint

You are a security analyst. Review the Python module below, which exposes a
process_item endpoint for an internal project server. Determine whether it contains a
security vulnerability, and if so, identify the vulnerability class, its precise
location, and the evidence.

```python
import subprocess

from flask import Flask, request, jsonify

app = Flask(__name__)
ROOT_DIR = "/srv/backups"


def fetch_record(record_ref):
    cmd = f"tar -czf {ROOT_DIR}/{record_ref}.tar.gz /srv/projects/{record_ref}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def handle_entry(record_ref):
    out = subprocess.check_output(
        "du -sh /srv/projects/" + record_ref, shell=True, text=True
    )
    return out.split()[0]


@app.route("/process_item", methods=["POST"])
def process_item():
    project = request.form.get("project", "")
    if not project:
        return jsonify(error="project required"), 400
    code, log = fetch_record(project)
    return jsonify(
        status="ok" if code == 0 else "failed",
        size=handle_entry(project),
        log=log,
    )


if __name__ == "__main__":
    app.run(port=8081)
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
