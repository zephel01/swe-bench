"""検出 grader (セキュリティ/解析).

モデルに脆弱性・侵害の「検出・診断」をさせ、gold ラベルとの
precision / recall / F1 で採点する。修正はしない。

出力契約: `--- FINDINGS ---` の後に JSON 配列
  [{"type": "...", "location": "...", "evidence": "..."}]
デコイ (gold.findings==[]) では予測 0 件が正解 (過検出を罰する)。
gold の `allow_extra` に合致した予測は **中立** (TP でも FP でもなく分母から除外)。
同じコードから読み取れる副次的だが妥当な指摘 (例: コマンドインジェクションの
コードに対する「認証が無い」) を過検出として罰しないための逃がし弁。
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


def _kw_hit(pred_text_lc: str, kw) -> bool:
    """keywords_all の1要素を判定する.

    文字列ならそのまま部分一致。リスト/タプルなら OR グループとして扱い、
    いずれか1つが含まれれば充足 (英日の表記ゆれ吸収用。例:
    ["travers", "トラバーサル"])。
    """
    if isinstance(kw, (list, tuple)):
        return any(str(x).lower() in pred_text_lc for x in kw)
    return str(kw).lower() in pred_text_lc


def _location_ok(pred: dict, g: dict) -> bool | None:
    """予測の location フィールドが gold の想定箇所に合っているか.

    gold に `location_any_of` が無ければ None (採点対象外)。
    evidence 全文ではなく location フィールドだけを見る — 根拠に関数名を
    書いておけば通る、という抜け道を塞ぐため。
    """
    terms = g.get("location_any_of")
    if not terms:
        return None
    loc = str(pred.get("location", "")).lower()
    if not loc.strip():
        return False
    return any(str(t).lower() in loc for t in terms)


def _covers(pred_text_lc: str, g: dict) -> bool:
    terms = [str(t) for t in g.get("any_of", [])]
    if g.get("cwe"):
        terms.append(str(g["cwe"]))
    any_ok = any(t.lower() in pred_text_lc for t in terms) if terms else True
    all_ok = all(_kw_hit(pred_text_lc, k) for k in g.get("keywords_all", []))
    return any_ok and all_ok


class DetectionGrader(Grader):
    name = "detection"
    domain = "security"

    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        return _SYSTEM, task.issue(lang)

    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        ev = GraderEval()
        gold_doc = _load_gold(task)
        gold = gold_doc.get("findings", [])
        allow_extra = gold_doc.get("allow_extra", [])
        preds, ok, err = _extract_findings(raw_output)
        ev.parse_ok = ok
        ev.parse_error = err
        ev.parsed_files = {"findings.json": json.dumps(preds, ensure_ascii=False, indent=2)}

        pred_texts = [_serialize(p) for p in preds]
        n_gold, n_pred = len(gold), len(preds)
        covered = [g for g in gold if any(_covers(pt, g) for pt in pred_texts)]

        # 予測を TP / 中立 / FP に振り分ける。
        # 中立 = allow_extra に合致した予測。precision の分母から除外する。
        tp, neutral, fp_texts = [], [], []
        for pt in pred_texts:
            if any(_covers(pt, g) for g in gold):
                tp.append(pt)
            elif allow_extra and any(_covers(pt, a) for a in allow_extra):
                neutral.append(pt)
            else:
                fp_texts.append(pt)
        n_scored = len(tp) + len(fp_texts)

        # location 採点 (gold に location_any_of がある finding のみ)。
        # 未検出の finding は recall 側で既に罰しているのでここでは数えない
        # (二重減点を避ける)。
        loc_graded = loc_correct = 0
        for g in gold:
            if not g.get("location_any_of"):
                continue
            hits = [pr for pr, pt in zip(preds, pred_texts) if _covers(pt, g)]
            if not hits:
                continue
            loc_graded += 1
            if any(_location_ok(pr, g) for pr in hits):
                loc_correct += 1
        location_acc = (loc_correct / loc_graded) if loc_graded else None

        recall = len(covered) / n_gold if n_gold else 1.0
        if n_scored:
            precision = len(tp) / n_scored
        else:
            precision = 1.0 if n_gold == 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        dcfg = ctx.graders_cfg.get("detection", {})
        pass_f1 = float(dcfg.get("pass_f1", 0.67))
        pass_recall = dcfg.get("pass_recall")
        max_fp_per_gold = dcfg.get("max_fp_per_gold")

        # (resolved は下の2軸ゲートで上書きされる)
        # 2軸ゲート (pass_recall と max_fp_per_gold が両方あるとき):
        #   合格 = 「本命を規定割合まで検出」かつ「余分が gold 件数×係数 以下」。
        # 単一 F1 閾値だと「余分の許容」と「取りこぼしの許容」を独立に決められず、
        # gold 1件のタスクでは F1 が 1.0 → 0.667 → 0.5 と飛ぶため 0.67 前後の
        # 閾値が実質「所見をちょうど1件だけ出せ」になってしまう。
        # 両キーが無ければ従来どおり F1 単独で判定する (後方互換)。
        fp_budget = None
        if pass_recall is not None and max_fp_per_gold is not None:
            fp_budget = int(float(max_fp_per_gold) * n_gold)   # デコイ(n_gold=0)は0件
            ev.resolved = (recall >= float(pass_recall)) and (len(fp_texts) <= fp_budget)
        else:
            ev.resolved = f1 >= pass_f1

        # quality: F1 に location 正答率を重み付きで掛ける。
        # location_weight=0 (既定) なら従来どおり F1×100。
        loc_w = float(dcfg.get("location_weight", 0.0))
        q = f1
        if location_acc is not None and loc_w > 0:
            q = f1 * (1.0 - loc_w + loc_w * location_acc)
        ev.quality_score = round(q * 100, 1)
        fp = len(fp_texts)
        fn = n_gold - len(covered)
        ev.components = {
            "detection": {
                "enabled": True,
                "precision": round(precision, 3), "recall": round(recall, 3),
                "f1": round(f1, 3), "tp": len(tp), "fp": fp, "fn": fn,
                "neutral": len(neutral),
                "n_gold": n_gold, "n_pred": n_pred, "n_scored": n_scored,
                "pass_f1": pass_f1,
                "gate": "recall+fp" if fp_budget is not None else "f1",
                "location_acc": (round(location_acc, 3)
                                 if location_acc is not None else None),
                "location_graded": loc_graded, "location_weight": loc_w,
                "pass_recall": pass_recall, "fp_budget": fp_budget,
                "decoy": n_gold == 0,
            }
        }
        missed = [g.get("id") or g.get("cwe") or "?" for g in gold if g not in covered]
        neutral_note = f" NEUTRAL={len(neutral)}" if neutral else ""
        ev.detail_output = (
            f"precision={precision:.2f} recall={recall:.2f} F1={f1:.2f} "
            f"(TP={len(tp)} FP={fp} FN={fn}{neutral_note}); missed={missed}"
            + (f"; location {loc_correct}/{loc_graded}" if loc_graded else "")
        )
        if not ev.resolved:
            if n_gold == 0 and n_scored > 0:
                ev.fail_reason = f"over-flagged {n_scored} false positive(s) on clean input"
            elif fp_budget is not None:
                if recall < float(pass_recall):
                    ev.fail_reason = (
                        f"recall {recall:.2f} < {pass_recall} (missed={missed})"
                    )
                else:
                    ev.fail_reason = (
                        f"over-flagged {fp} finding(s), budget {fp_budget} "
                        f"(recall {recall:.2f} OK)"
                    )
            else:
                ev.fail_reason = f"F1 {f1:.2f} < {pass_f1} (missed={missed})"
        return ev

    def mock_gold(self, task) -> str:
        gold = _load_gold(task).get("findings", [])
        preds = []
        for g in gold:
            ev = " ".join(str(t) for t in g.get("any_of", []))
            kws = [
                str(k[0]) if isinstance(k, (list, tuple)) and k else str(k)
                for k in g.get("keywords_all", [])
            ]
            ev += " " + " ".join(kws)
            loc_terms = g.get("location_any_of") or []
            preds.append({
                "type": g.get("cwe", g.get("id", "issue")),
                "location": str(loc_terms[0]) if loc_terms else "see code",
                "evidence": ev.strip(),
            })
        body = json.dumps(preds, ensure_ascii=False, indent=2)
        return f"--- FINDINGS ---\n{body}"

    def mock_broken(self, task) -> str:
        # 架空の finding を1件出す → デコイでは FP、非デコイでは recall0 → 必ず失敗。
        bogus = [{"type": "made-up issue", "location": "nowhere",
                  "evidence": "zzzzz nonexistent token qqqqq"}]
        return "--- FINDINGS ---\n" + json.dumps(bogus, ensure_ascii=False)
