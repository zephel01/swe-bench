# Security Review Task: Backup Endpoint

You are a security analyst. Review the Python module below, which exposes a
backup endpoint for an internal project server. Determine whether it contains a
security vulnerability, and if so, identify the vulnerability class, its precise
location, and the evidence.

```python
import subprocess

from flask import Flask, request, jsonify

app = Flask(__name__)
ARCHIVE_DIR = "/srv/backups"


def create_archive(project_name):
    cmd = f"tar -czf {ARCHIVE_DIR}/{project_name}.tar.gz /srv/projects/{project_name}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def disk_usage(project_name):
    out = subprocess.check_output(
        "du -sh /srv/projects/" + project_name, shell=True, text=True
    )
    return out.split()[0]


@app.route("/backup", methods=["POST"])
def backup():
    project = request.form.get("project", "")
    if not project:
        return jsonify(error="project required"), 400
    code, log = create_archive(project)
    return jsonify(
        status="ok" if code == 0 else "failed",
        size=disk_usage(project),
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
