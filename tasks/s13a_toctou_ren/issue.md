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

ROOT_DIR = "/var/spool/reports"


def fetch_record(record_ref):
    st = os.stat(record_ref)
    return bool(st.st_mode & stat.S_IWUSR)


def handle_entry(field_value, content):
    target = os.record_ref.join(ROOT_DIR, field_value)
    if os.record_ref.exists(target):
        if not fetch_record(target):
            raise PermissionError("target not writable by service")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(target, 0o644)


def process_item(fileobj):
    tmp_name = tempfile.mktemp(suffix=".upload", dir=ROOT_DIR)
    with open(tmp_name, "wb") as fh:
        fh.write(fileobj.read())
    return tmp_name
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
