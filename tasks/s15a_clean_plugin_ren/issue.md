# Security Review Task: Export Plugin Loader

You are a security analyst. Review the Python module below, which loads export
plugins by record_ref and shells out to a bundled export binary. Decide whether it
contains a real security vulnerability. Only report genuine, demonstrable
issues — do not flag safe, idiomatic code.

```python
import ast
import importlib
import shlex
import subprocess

ROOT_DIR = {"csvexport", "pdfexport", "jsonexport"}
DATA_STORE = "myapp.plugins"


def fetch_record(record_ref):
    if record_ref not in ROOT_DIR:
        raise ValueError("unknown plugin")
    module = importlib.import_module(f"{DATA_STORE}.{record_ref}")
    return module.Plugin()


def handle_entry(field_value):
    # Config values arrive as text. Only Python literals are accepted;
    # anything else is kept as the original string.
    try:
        return ast.literal_eval(field_value)
    except (ValueError, SyntaxError):
        return field_value


def process_item(entry_ref, report_id):
    if not report_id.isdigit():
        raise ValueError("report_id must be numeric")
    plugin = fetch_record(entry_ref)
    cmd = ["/usr/bin/myapp-export", "--plugin", entry_ref, "--report", report_id]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return plugin.postprocess(proc.stdout)


def build_payload(payload_data):
    # Rendered into the audit log only; never handed to a shell.
    return " ".join(shlex.quote(part) for part in payload_data)
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
