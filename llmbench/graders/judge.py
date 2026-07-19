"""文章品質 grader (創作 / rubric + judge) — 実験的.

オラクルが無いため rubric + judge モデルに依存する (未較正・experimental)。
まず hard_constraints を決定的ゲートとして評価し、judge クライアントがあれば
rubric で 0-10 採点する。judge が無い場合 (validate/mock 含む) は hard_constraints
のみで判定するため、検証は決定的に緑を保てる。

出力契約: `--- ANSWER ---` の後に文章本文。
"""

from __future__ import annotations

import json
import re

from . import GradeCtx, Grader, GraderEval
from .checks import extract_answer, run_checks

_SYSTEM = """\
You are a skilled writer. Follow the brief and any hard constraints (e.g. length).
Put your final answer after a line `--- ANSWER ---`.
"""

_JUDGE_SYSTEM = """\
You are a strict, fair writing judge. Score the candidate text from 0 to 10 against
the given criteria. Respond ONLY with JSON: {"score": <0-10 number>, "reason": "<one sentence>"}
"""


def _load_rubric(task) -> dict:
    p = task.dir / "rubric.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _parse_score(text: str):
    m = re.search(r'"score"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text or "")
    if m:
        return max(0.0, min(10.0, float(m.group(1))))
    m = re.search(r"\b([0-9]|10)(?:\.[0-9]+)?\s*/\s*10", text or "")
    if m:
        return max(0.0, min(10.0, float(m.group(1))))
    return None


def _judge_prompt(task, rubric: dict, answer: str, lang: str) -> str:
    crit = "\n".join(
        f"- {c.get('name')}: {c.get('desc', '')} (weight {c.get('weight', 1.0)})"
        for c in rubric.get("criteria", [])
    )
    return (
        f"# Brief\n{task.issue(lang)}\n\n# Criteria\n{crit}\n\n"
        f"# Candidate answer\n{answer}\n\n"
        'Score 0-10. JSON only: {"score": N, "reason": "..."}'
    )


class JudgeGrader(Grader):
    name = "judge"
    domain = "writing"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        return _SYSTEM, task.issue(lang)

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        answer = extract_answer(raw_output)
        rubric = _load_rubric(task)
        ev.parse_ok = bool(answer)
        ev.parsed_files = {"answer.txt": answer}

        hard = run_checks(answer, rubric.get("hard_constraints", []))
        hard_pass = all(r["passed"] for r in hard)
        hard_failed = [f"{r['kind']}({r['detail']})" for r in hard if not r["passed"]]
        pass_score = float(
            ctx.graders_cfg.get("judge", {}).get("pass_score", rubric.get("pass_score", 7.0))
        )

        comp = {
            "enabled": True, "judged": False,
            "hard_pass": hard_pass, "hard_checks": hard,
        }

        # judge 無し or hard 不合格 → 決定的判定
        if ctx.judge is None or not hard_pass:
            ev.resolved = hard_pass
            ev.quality_score = 100.0 if hard_pass else 0.0
            comp["note"] = "no judge (deterministic hard-constraint gate only)" \
                if ctx.judge is None else "hard constraints failed"
            ev.components = {"judge": comp}
            ev.detail_output = (
                f"hard_constraints {'PASS' if hard_pass else 'FAIL'}"
                + (f"; failed {hard_failed}" if hard_failed else "")
                + (" ; judge skipped" if ctx.judge is None else "")
            )
            if not ev.resolved:
                ev.fail_reason = f"hard constraints failed: {hard_failed}"
            return ev

        # judge あり → seeds 回採点して平均
        seeds = max(1, int(ctx.judge_seeds))
        prompt = _judge_prompt(task, rubric, answer, ctx.lang)
        scores = []
        for _ in range(seeds):
            try:
                gen = ctx.judge.generate(_JUDGE_SYSTEM, prompt)
                s = _parse_score(gen.text)
                if s is not None:
                    scores.append(s)
            except Exception as e:
                comp.setdefault("errors", []).append(str(e))
        if not scores:
            # judge 応答不良 → hard ゲートのみで妥協
            ev.resolved = hard_pass
            ev.quality_score = 100.0 if hard_pass else 0.0
            comp["note"] = "judge produced no parseable score; fell back to hard gate"
            ev.components = {"judge": comp}
            ev.detail_output = "judge unparseable; hard gate only"
            return ev
        mean = sum(scores) / len(scores)
        comp.update({
            "judged": True, "scores": scores, "mean_score": round(mean, 2),
            "spread": round(max(scores) - min(scores), 2), "pass_score": pass_score,
        })
        ev.resolved = hard_pass and mean >= pass_score
        ev.quality_score = round(mean * 10, 1)
        ev.components = {"judge": comp}
        ev.detail_output = (
            f"judge mean={mean:.1f}/10 (n={len(scores)}, spread={comp['spread']}) "
            f"pass≥{pass_score}; hard {'PASS' if hard_pass else 'FAIL'}"
        )
        if not ev.resolved:
            ev.fail_reason = f"judge {mean:.1f} < {pass_score}"
        return ev

    def mock_gold(self, task) -> str:
        p = task.dir / "gold_answer.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def mock_broken(self, task) -> str:
        return "x"
