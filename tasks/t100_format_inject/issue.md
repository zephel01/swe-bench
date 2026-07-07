# Bug: template renderer exposes object internals through format fields

`safe_format(template, *args, **kwargs)` renders a user-supplied `template`
against caller-supplied values. It is only meant to substitute plain named or
positional fields. Instead, a template can reach into the internals of the
substituted values.

Reported problems (all must raise `ValueError` instead of rendering):

- `safe_format("{x.__class__}", x=1)` exposes the type of `x`.
- `safe_format("{0.__class__.__init__.__globals__}", object())` reaches module
  globals.
- `safe_format("{conf[secret]}", conf={"secret": "s3cr3t"})` indexes into a
  passed object.

Ordinary templates must keep working:

- `safe_format("{name} is {age}", name="Bob", age=42)` -> `"Bob is 42"`.
- `safe_format("{0}-{1}", "a", "b")` -> `"a-b"`.
- `safe_format("{{literal}}")` -> `"{literal}"`.
- `safe_format("{0:>5}", "hi")` -> `"   hi"` and `safe_format("{0!r}", "hi")`
  -> `"'hi'"`.
