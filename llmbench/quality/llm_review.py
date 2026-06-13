"""LLMレビュー採点: 別LLM(または同一LLM)にpatchを0-10点でレビューさせる."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..prompts import REVIEW_SYSTEM, build_review_prompt

JSON_RE = re.compile(r"\{[^{}]*\"score\"[^{}]*\}", re.DOTALL)


def llm_review_score(
    workspace: Path,
    changed_files: list[str],
    cfg: dict,
    issue_text: str,
    reviewer_client,
) -> tuple[float | None, dict]:
    if reviewer_client is None:
        return None, {"reason": "reviewer client not configured"}
    patched = {
        f: (workspace / f).read_text(encoding="utf-8") for f in changed_files
    }
    result = reviewer_client.generate(
        REVIEW_SYSTEM, build_review_prompt(issue_text, patched)
    )
    m = JSON_RE.search(result.text)
    if not m:
        return None, {"reason": "reviewer output not parseable",
                      "raw": result.text[:200]}
    try:
        data = json.loads(m.group(0))
        raw_score = float(data.get("score", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, {"reason": "invalid JSON from reviewer"}
    score = max(0.0, min(10.0, raw_score)) * 10.0  # 0-10 → 0-100
    return score, {"reviewer": reviewer_client.name,
                   "reason": str(data.get("reason", ""))[:200]}
