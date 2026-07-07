# Bug: safe path join lets crafted inputs escape the base directory

`resolve_subpath(base, user_path)` is meant to take an untrusted `user_path`
and return the resolved location **only if it stays inside `base`**, otherwise
`None`. Users report that some inputs which clearly point outside `base` are
accepted, while some perfectly ordinary names are handled correctly.

Observed accepted-but-should-be-rejected cases:

- `%252e%252e%252fetc/passwd` resolves to something treated as safe.
- `..\..\etc\passwd` (backslashes) is treated as safe.
- `．．／etc/passwd` (fullwidth dots and slash) is treated as safe.
- With `base="/srv/data"`, the input `../data_backup/x` comes back non-`None`.

Ordinary inputs already behave correctly and must keep working:

- `docs/report.pdf` resolves under the base.
- `./notes.txt` resolves under the base.
- `archive..bak/file.txt` (a real filename that merely contains dots) is
  accepted, not rejected.
