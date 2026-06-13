"""プロンプトテンプレート."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an expert software engineer fixing bugs in a Python codebase.
You will receive a bug report (issue) and the current source files.
Fix the bug. Output ONLY the complete corrected file(s) using EXACTLY this format:

--- FILE: <relative/path.py> ---
```python
<entire corrected file content>
```

Rules:
- Output the ENTIRE file content for every file you change, not a diff.
- Only include files that need changes.
- Do not change test files.
- Keep the fix minimal, readable and idiomatic. Do not refactor unrelated code.
"""


def build_user_prompt(issue: str, files: dict[str, str]) -> str:
    parts = [f"# Bug report\n\n{issue}\n", "# Current source files\n"]
    for path, content in files.items():
        parts.append(f"--- FILE: {path} ---\n```python\n{content}\n```\n")
    parts.append("Fix the bug now. Remember the required output format.")
    return "\n".join(parts)


REVIEW_SYSTEM = """\
You are a strict senior code reviewer. Score the given bug-fix patch from 0 to 10:
- correctness-risk, readability, maintainability, security, idiomatic style.
Respond ONLY with JSON: {"score": <0-10 integer>, "reason": "<one sentence>"}
"""


def build_review_prompt(issue: str, patched_files: dict[str, str]) -> str:
    parts = [f"# Issue that was fixed\n\n{issue}\n", "# Patched files\n"]
    for path, content in patched_files.items():
        parts.append(f"--- FILE: {path} ---\n```python\n{content}\n```\n")
    parts.append('Score this patch. JSON only: {"score": N, "reason": "..."}')
    return "\n".join(parts)
