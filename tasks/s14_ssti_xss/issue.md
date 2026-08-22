# Security Review Task: Note Rendering Service

You are a security analyst. Review the Python module below, which renders greeting
and note pages for an internal web tool. Determine whether it contains
security vulnerabilities, and if so, identify every vulnerability class, its
precise location, and the evidence. Report each distinct issue as a separate
finding.

```python
from flask import Flask, request, render_template_string
from markupsafe import Markup

app = Flask(__name__)
app.secret_key = "dev-secret-key"

PAGE = "<html><body><h1>{title}</h1><div>{body}</div></body></html>"


@app.route("/greet")
def greet():
    name = request.args.get("name", "guest")
    template = "<p>Hello, " + name + "!</p>"
    return render_template_string(template)


@app.route("/note")
def note():
    text = request.args.get("text", "")
    return PAGE.format(title="Note", body=Markup(text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
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
