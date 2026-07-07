# Context views drop a line and lose the trailing newline

`context_view(text, start, end, context)` returns the block of lines around a
changed region `[start, end)`, including up to `context` lines of surrounding
context, as text. Two problems:

- The block that comes back is missing one line of trailing context — the
  window is one line too short below the change.
- When the source text ends with a newline, the returned block loses that
  final newline, so the text no longer round-trips.

Changes near the end of the file, and text without a trailing newline, look
correct.
