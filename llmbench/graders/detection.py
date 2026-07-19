"""検出 grader (セキュリティ/解析).

モデルに脆弱性・侵害の「検出・診断」をさせ、gold ラベルとの
precision / recall / F1 で採点する。修正はしない。

出力契約: `--- FINDINGS ---` の後に JSON 配列
  [{"type": "...", "location": "...", "evidence": "..."}]
デコイ (gold.findings==[]) では予測 0 件が正解 (過検出を罰する)。
"""

from __future__ import annotations

import json
import re

from . import GradeCtx, Grader, GraderEval
from ..patch import _strip_control_tokens

_SYSTEM = """\
You are a senior security analyst. Analyze the provided code or log and report
security issues you find. Output ONLY a JSON array after a line `--- FINDINGS ---`.
Each element: {"type": "<vuln class / CWE>", "location": "<where>", "evidence": "<the exact risky snippet>"}.
If there are NO issues, output an empty array: []
Do not include any other text after the JSON.
"""


def _load_gold(task) -> dict:
    p = task.dir / "gold.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"findings": []}


def _first_json_array(text: str):
    """テキスト中の最初の妥当な JSON 配列を返す (無ければ None)."""
    i = 0
    while True:
        start = text.find("[", i)
        if start < 0:
            return None
        depth, in_str, esc = 0, False, False
        for j in range(start, len(text)):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:j + 1])
                        except Exception:
                            break
        i = start + 1


def _extract_findings(raw: str):
    """モデル出力から findings 配列を抽出する. (list, parse_ok, error)."""
    text = _strip_control_tokens(raw or "")
    if not text.strip():
        return [], False, "empty output"
    m = re.search(r"-{2,}\s*FINDINGS\s*-{2,}", text, re.I)
    seg = text[m.end():] if m else text
    arr = _first_json_array(seg)
    if arr is None and m is None:
        arr = _first_json_array(text)
    if arr is None:
        return [], False, "no JSON findings array found"
    norm = []
    for it in arr:
        if isinstance(it, dict):
            norm.append(it)
        else:
            norm.append({"type": str(it)})
    return norm, True, ""


def _serialize(pred: dict) -> str:
    return json.dumps(pred, ensure_ascii=False).lower()


def _covers(pred_text_lc: str, g: dict) -> bool:
    terms = [str(t) for t in g.get("any_of", [])]
    if g.get("cwe"):
        terms.append(str(g["cwe"]))
    any_ok = any(t.lower() in pred_text_lc for t in terms) if terms else True
    all_ok = all(str(k).lower() in pred_text_lc for k in g.get("keywords_all", []))
    return any_ok and all_ok


class DetectionGrader(Grader):
    name = "detection"
    domain = "security"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        return _SYSTEM, task.issue(lang)

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        gold = _load_gold(task).get("findings", [])
        preds, ok, err = _extract_findings(raw_output)
        ev.parse_ok = ok
        ev.parse_error = err
        ev.parsed_files = {"findings.json": json.dumps(preds, ensure_ascii=False, indent=2)}

        pred_texts = [_serialize(p) for p in preds]
        n_gold, n_pred = len(gold), len(preds)
        covered = [g for g in gold if any(_covers(pt, g) for pt in pred_texts)]
        tp = [pt for pt in pred_texts if any(_covers(pt, g) for g in gold)]

        recall = len(covered) / n_gold if n_gold else 1.0
        if n_pred:
            precision = len(tp) / n_pred
        else:
            precision = 1.0 if n_gold == 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        pass_f1 = float(ctx.graders_cfg.get("detection", {}).get("pass_f1", 0.67))
        ev.resolved = f1 >= pass_f1
        ev.quality_score = round(f1 * 100, 1)
        fp = n_pred - len(tp)
        fn = n_gold - len(covered)
        ev.components = {
            "detection": {
                "enabled": True,
                "precision": round(precision, 3), "recall": round(recall, 3),
                "f1": round(f1, 3), "tp": len(tp), "fp": fp, "fn": fn,
                "n_gold": n_gold, "n_pred": n_pred, "pass_f1": pass_f1,
                "decoy": n_gold == 0,
            }
        }
        missed = [g.get("id") or g.get("cwe") or "?" for g in gold if g not in covered]
        ev.detail_output = (
            f"precision={precision:.2f} recall={recall:.2f} F1={f1:.2f} "
            f"(TP={len(tp)} FP={fp} FN={fn}); missed={missed}"
        )
        if not ev.resolved:
            if n_gold == 0 and n_pred > 0:
                ev.fail_reason = f"over-flagged {n_pred} false positive(s) on clean input"
            else:
                ev.fail_reason = f"F1 {f1:.2f} < {pass_f1} (missed={missed})"
        return ev

    def mock_gold(self, task) -> str:
        gold = _load_gold(task).get("findings", [])
        preds = []
        for g in gold:
            ev = " ".join(str(t) for t in g.get("any_of", []))
            ev += " " + " ".join(str(k) for k in g.get("keywords_all", []))
            preds.append({
                "type": g.get("cwe", g.get("id", "issue")),
                "location": "see code",
                "evidence": ev.strip(),
            })
        body = json.dumps(preds, ensure_ascii=False, indent=2)
        return f"--- FINDINGS ---\n{body}"

    def mock_broken(self, task) -> str:
        # 架空の finding を1件出す → デコイでは FP、非デコイでは recall0 → 必ず失敗。
        bogus = [{"type": "made-up issue", "location": "nowhere",
                  "evidence": "zzzzz nonexistent token qqqqq"}]
        return "--- FINDINGS ---\n" + json.dumps(bogus, ensure_ascii=False)
