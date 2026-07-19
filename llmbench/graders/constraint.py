"""制約遵守 grader (一般タスク / IFEval 方式).

モデルの回答をプログラムで検証可能なチェック配列 (checks.json) で採点する。
judge 不要の完全客観。コーダー特化モデルの「一般退化」が可視化される。

出力契約: `--- ANSWER ---` の後に回答本文 (無ければ全文を回答とみなす)。
- resolved = 全チェック通過 (instruction-strict accuracy)
- quality  = 通過数 / 総数 × 100 (instruction-level accuracy)
"""

from __future__ import annotations

import json

from . import GradeCtx, Grader, GraderEval
from .checks import extract_answer, run_checks

_SYSTEM = """\
You are a careful assistant. Follow ALL formatting and content constraints in the
task exactly. Put your final answer after a line `--- ANSWER ---` and nothing else after it.
"""


def _load_checks(task) -> list[dict]:
    p = task.dir / "checks.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


class ConstraintGrader(Grader):
    name = "constraint"
    domain = "general"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        return _SYSTEM, task.issue(lang)

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        answer = extract_answer(raw_output)
        checks = _load_checks(task)
        ev.parse_ok = bool(answer)
        ev.parsed_files = {"answer.txt": answer}
        if not answer:
            ev.parse_error = "empty answer"
        results = run_checks(answer, checks)
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        frac = passed / total if total else 0.0
        pass_ratio = float(ctx.graders_cfg.get("constraint", {}).get("pass_ratio", 1.0))
        ev.resolved = total > 0 and frac >= pass_ratio
        ev.quality_score = round(frac * 100, 1)
        ev.components = {
            "constraint": {
                "enabled": True, "passed": passed, "total": total,
                "checks": results,
            }
        }
        failed = [f"{r['kind']}({r['detail']})" for r in results if not r["passed"]]
        ev.detail_output = f"{passed}/{total} checks passed" + (
            f"; failed: {failed}" if failed else ""
        )
        if not ev.resolved:
            ev.fail_reason = f"{passed}/{total} checks passed" + (
                f"; failed {failed}" if failed else ""
            )
        return ev

    def mock_gold(self, task) -> str:
        p = task.dir / "gold_answer.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def mock_broken(self, task) -> str:
        return "x"  # 1語・非JSON・マーカー無し → ほぼ全チェックを落とす
