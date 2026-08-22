# Security Review Task: Export Plugin Loader

You are a security analyst. Review the Python module below, which loads export
plugins by name and shells out to a bundled export binary. Decide whether it
contains a real security vulnerability. Only report genuine, demonstrable
issues — do not flag safe, idiomatic code.

```python
import ast
import importlib
import shlex
import subprocess

ALLOWED_PLUGINS = {"csvexport", "pdfexport", "jsonexport"}
PLUGIN_PACKAGE = "myapp.plugins"


def load_plugin(name):
    if name not in ALLOWED_PLUGINS:
        raise ValueError("unknown plugin")
    module = importlib.import_module(f"{PLUGIN_PACKAGE}.{name}")
    return module.Plugin()


def parse_setting(raw):
    # Config values arrive as text. Only Python literals are accepted;
    # anything else is kept as the original string.
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def run_export(plugin_name, report_id):
    if not report_id.isdigit():
        raise ValueError("report_id must be numeric")
    plugin = load_plugin(plugin_name)
    cmd = ["/usr/bin/myapp-export", "--plugin", plugin_name, "--report", report_id]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return plugin.postprocess(proc.stdout)


def describe(cmd_parts):
    # Rendered into the audit log only; never handed to a shell.
    return " ".join(shlex.quote(part) for part in cmd_parts)
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
