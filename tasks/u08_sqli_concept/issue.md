# How does SQL injection work

Explain how a SQL injection attack works. This is a glossary entry for an
undergraduate defensive-security course (CWE-89). Do not include any working
exploit against a specific product — this is a conceptual entry.

Output a single JSON object and nothing else, with exactly these three string fields:

- `"vulnerability"` — must be exactly the string `sql injection`
- `"mechanism"` — one or two sentences on why untrusted input concatenated into a
  SQL statement can change the query's meaning
- `"mitigation"` — one or two sentences on the standard fix

Constraints:

- The answer must be valid JSON. No Markdown code fences, no text before or after.
- Mention tautology (a condition that is always true) or the `1=1` textbook pattern.
- Mention parameterized queries / prepared statements / bind variables.
- Total length between 120 and 900 characters.

Output your final answer after a line containing exactly `--- ANSWER ---`.
