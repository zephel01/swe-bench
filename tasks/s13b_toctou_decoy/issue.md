# Security Review Task: Report Spooler Daemon

You are a security analyst. Review the Python module below, which belongs to a
daemon that runs as root and publishes generated reports into a spool directory
that is also writable by a lower-privileged upload service. Determine whether it
contains security vulnerabilities, and if so, identify every vulnerability
class, its precise location, and the evidence. Report each distinct issue as a
separate finding.

```python
import os
import stat
import tempfile

SPOOL_DIR = "/var/spool/reports"


def is_writable_by_service(path):
    st = os.stat(path)
    return bool(st.st_mode & stat.S_IWUSR)


def publish_report(name, content):
    target = os.path.join(SPOOL_DIR, name)
    if os.path.exists(target):
        if not is_writable_by_service(target):
            raise PermissionError("target not writable by service")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(target, 0o644)


def stage_upload(fileobj):
    tmp_name = tempfile.mktemp(suffix=".upload", dir=SPOOL_DIR)
    with open(tmp_name, "wb") as fh:
        fh.write(fileobj.read())
    return tmp_name


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
