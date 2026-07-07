# Bug: archive extractor accepts members that escape the destination

`safe_member_path(dest, name)` takes an extraction directory `dest` (an
absolute path) and an archive member `name`, and returns the absolute path the
member would be written to **only if it stays inside `dest`**, otherwise
`None`. Some members that resolve outside `dest` are returned as if safe.

With `dest="/tmp/extract"`:

- `"../extract_evil/secret"` is returned non-`None`, even though it resolves to
  `/tmp/extract_evil/secret`, a sibling directory outside `dest`.
- `"..\\..\\etc\\passwd"` (backslash separators) is returned non-`None`.

Legitimate members must still be accepted, and clearly hostile ones rejected:

- `"sub/file.txt"`, `"reports/2024/q1.csv"` return a path inside `dest`.
- `"notes..txt"` (a real filename that merely contains dots) is accepted.
- `"../../etc/passwd"` and `"/etc/passwd"` return `None`.
