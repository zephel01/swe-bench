"""知識QA grader (医療など) — 参考値.

回答をgoldキーと照合する。MCQは選択肢文字、短答はキーワード一致。
医療ドメインは「参考値 (reference)」であり臨床的妥当性の保証ではない。

出力契約: `--- ANSWER ---` の後に回答 (MCQは選択肢文字、短答は用語)。
gold.json:
  {"mode": "mcq", "answer": "C"}
  {"mode": "keyword", "all": ["ace inhibitor"], "any": ["acei", "lisinopril"]}
"""

from __future__ import annotations

import json
import re

from . import GradeCtx, Grader, GraderEval
from .checks import extract_answer

_SYSTEM = """\
Answer the question. Put your final answer after a line `--- ANSWER ---`.
For multiple choice, give just the letter. For short answer, give the term.
"""


def _load_gold(task) -> dict:
    p = task.dir / "gold.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _mcq_letter(answer: str) -> str | None:
    """回答から選択肢文字 (A-E) を抽出する."""
    m = re.search(r"answer\s*(?:is|:)?\s*\(?([A-Ea-e])\b", answer, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"(?<![A-Za-z])([A-Ea-e])(?![A-Za-z])", answer)
    return m.group(1).upper() if m else None


class QaGrader(Grader):
    name = "qa"
    domain = "general"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        return _SYSTEM, task.issue(lang)

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        answer = extract_answer(raw_output)
        gold = _load_gold(task)
        ev.parse_ok = bool(answer)
        ev.parsed_files = {"answer.txt": answer}
        mode = gold.get("mode", "keyword")

        if mode == "mcq":
            got = _mcq_letter(answer)
            want = str(gold.get("answer", "")).upper()
            ok = got == want and bool(want)
            ev.resolved = ok
            ev.quality_score = 100.0 if ok else 0.0
            ev.components = {"qa": {"enabled": True, "mode": "mcq",
                                    "got": got, "want": want}}
            ev.detail_output = f"MCQ got={got} want={want}"
            if not ok:
                ev.fail_reason = f"MCQ answer {got} != {want}"
            return ev

        # keyword mode
        low = answer.lower()
        need_all = [str(t).lower() for t in gold.get("all", [])]
        need_any = [str(t).lower() for t in gold.get("any", [])]
        all_ok = all(t in low for t in need_all)
        any_ok = (not need_any) or any(t in low for t in need_any)
        ok = all_ok and any_ok
        matched_all = sum(1 for t in need_all if t in low)
        ev.resolved = ok
        if ok:
            ev.quality_score = 100.0
        else:
            denom = len(need_all) + (1 if need_any else 0)
            hits = matched_all + (1 if (need_any and any_ok) else 0)
            ev.quality_score = round(hits / denom * 100, 1) if denom else 0.0
        ev.components = {"qa": {"enabled": True, "mode": "keyword",
                                "all_ok": all_ok, "any_ok": any_ok,
                                "need_all": need_all, "need_any": need_any}}
        ev.detail_output = f"keyword all_ok={all_ok} any_ok={any_ok}"
        if not ok:
            ev.fail_reason = "missing required keyword(s)"
        return ev

    def mock_gold(self, task) -> str:
        gold = _load_gold(task)
        if gold.get("mode") == "mcq":
            return f"--- ANSWER ---\n{gold.get('answer', '')}"
        parts = list(gold.get("all", []))
        if gold.get("any"):
            parts.append(gold["any"][0])
        return "--- ANSWER ---\n" + " ".join(str(p) for p in parts)

    def mock_broken(self, task) -> str:
        gold = _load_gold(task)
        if gold.get("mode") == "mcq":
            return "--- ANSWER ---\nZ"   # A-E に無い → 不一致
        return "--- ANSWER ---\nzzzzz"
