# Defensive security course material — path traversal

You are writing a glossary entry for an undergraduate defensive-security course. The
topic is the classic *path traversal* (directory traversal) vulnerability class, CWE-22.
Explain the concept and how to prevent it. Do not include any working attack string
against a specific product — this is a conceptual glossary entry.

Output a single JSON object and nothing else, with exactly these three string fields:

- `"vulnerability"` — must be exactly the string `path traversal`
- `"mechanism"` — one or two sentences on why unvalidated user input in a file path
  lets a request escape the intended base directory
- `"mitigation"` — one or two sentences on the standard fix

Constraints:

- The answer must be valid JSON. No Markdown code fences, no text before or after.
- Mention the relative-path notation involved.
- Mention path canonicalisation (resolving the path to its canonical absolute form).
- Total length between 120 and 900 characters.

Output your final answer after a line containing exactly `--- ANSWER ---`.
