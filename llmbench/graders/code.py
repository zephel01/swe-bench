"""コード修正 grader (既存パイプラインのラップ).

既存の parse_llm_output → evaluate_functional → evaluate_quality → combined_score を
そのまま Grader インターフェイスに載せる。スコア・validate 結果は現状と完全一致 (後方互換)。
"""

from __future__ import annotations

from . import GradeCtx, Grader, GraderEval
from .. import sandbox
from ..functional import evaluate_functional
from ..patch import parse_llm_output
from ..prompts import SYSTEM_PROMPT, build_user_prompt
from ..quality import evaluate_quality


class CodeGrader(Grader):
    name = "code"
    domain = "code"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        issue = task.issue(lang)
        return SYSTEM_PROMPT, build_user_prompt(issue, task.read_buggy_files())

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        patch = parse_llm_output(raw_output, task.files)
        ev.parse_ok = patch.parse_ok
        ev.parse_error = patch.error
        ev.parsed_files = dict(patch.files)

        func, ws = evaluate_functional(
            task.dir, patch, ctx.work_root, timeout=ctx.timeout, keep_workspace=True
        )
        ev.resolved = func.resolved
        ev.fail_reason = func.fail_reason
        ev.detail_output = func.test_output
        try:
            if ws is not None and func.applied_files:
                q = evaluate_quality(
                    ws, func.applied_files, ctx.quality_cfg,
                    issue_text=task.issue(ctx.lang), reviewer_client=ctx.reviewer,
                )
                ev.quality_score = q.score
                ev.components = q.components
        finally:
            if ws is not None:
                sandbox.cleanup(ws)
        return ev

    def mock_gold(self, task) -> str:
        gold = task.dir / "gold"
        blocks = []
        for f in sorted(gold.rglob("*.py")):
            rel = f.relative_to(gold)
            blocks.append(f"--- FILE: {rel} ---\n```python\n{f.read_text()}\n```")
        return "修正は以下の通りです。\n\n" + "\n\n".join(blocks)

    def mock_broken(self, task) -> str:
        return "raise SyntaxError(  # 壊れた出力 (フォーマット不正かつ非Python)"
