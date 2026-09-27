#!/usr/bin/env python3
"""llmbench security (detection) 結果の失敗モード分類.

v1 からの変更:
  - 「出力なしで合格」した試行を検出し、補正後の成功率を出す
    (detection grader がデコイで空出力を合格にしていた不具合の影響を見積もる)
      pass_no_output  合格 かつ 思考打ち切り (llmbench:reasoning_*) = 本文未出力が確定
      pass_truncated  合格 かつ max_tokens 打ち切り (本文があった可能性あり = 要確認)
  - 打ち切り理由 (reasoning_loop / reasoning_budget / length) を試行単位で集計
  - --scan DIR : DIR 内の全 *_results.json を走査し、影響のあった run だけ一覧

使い方:
  python3 tools/sec_classify.py results/<stamp>_<model>_results.json
  python3 tools/sec_classify.py --scan results/
"""
import collections
import json
import re
import sys
from pathlib import Path

REFUSAL = re.compile(r"I can(?:'|no)t (?:help|assist)|I'm sorry, but|申し訳ありませんが|お手伝いできません", re.I)
TAGS = re.compile(r"</?think>|</?thinking>|<tool_call>|<\|im_start\|>|<function=", re.I)
MARK = re.compile(r"-{2,}\s*FINDINGS\s*-{2,}", re.I)


def is_decoy(r):
    c = (r.get("quality_components") or {}).get("detection") or {}
    return bool(c.get("decoy")) or c.get("n_gold") == 0


def attempt_flags(r, a):
    """1試行の打ち切り/出力なし合格フラグ."""
    fr = a.get("finish_reason") or ""
    f = set()
    if fr.startswith("llmbench:reasoning"):
        f.add(fr.split(":", 1)[1])          # reasoning_loop / reasoning_budget
    elif a.get("truncated"):
        f.add("length")
    if a.get("resolved") and is_decoy(r):
        if fr.startswith("llmbench:reasoning"):
            f.add("pass_no_output")
        elif a.get("truncated"):
            f.add("pass_truncated")
    return f


def corrected(r):
    """(補正前 成功率, 補正後 成功率, 出力なし合格の試行数)."""
    att = [a for a in r.get("attempts", []) if not a.get("errored") and not a.get("skipped")]
    if not att:
        sr = r.get("success_rate", 1.0 if r.get("resolved") else 0.0)
        return sr, sr, 0
    bad = sum(1 for a in att if "pass_no_output" in attempt_flags(r, a))
    ok = sum(1 for a in att if a.get("resolved"))
    return ok / len(att), (ok - bad) / len(att), bad


def classify(r, raw):
    tags = set()
    comp = (r.get("quality_components") or {}).get("detection", {})
    if r.get("refused") or r.get("n_refused"):
        tags.add("refused")
    if r.get("n_errored"):
        tags.add("errored")
    if r.get("parse_ok") is False:
        tags.add("parse_fail")
    for a in r.get("attempts", []):
        tags |= attempt_flags(r, a)
    if raw is not None:
        if TAGS.search(raw):
            tags.add("tag_leak")
        if raw.strip() and not MARK.search(raw):
            tags.add("no_marker")
        if "refused" not in tags and REFUSAL.search(raw[:2000]):
            tags.add("refused?")
    reasons = " | ".join(a.get("fail_reason", "") for a in r.get("attempts", []) if not a.get("resolved"))
    if "clean input" in reasons:
        tags.add("decoy_fp")
    elif "over-flagged" in reasons:
        tags.add("over_flag")
    if re.search(r"recall [\d.]+ <", reasons):
        tags.add("missed")
    if "no findings output" in reasons:
        tags.add("no_output_fail")
    la = comp.get("location_acc")
    if la is not None and la < 1.0:
        tags.add("location")
    return sorted(tags), comp, reasons


def load(path):
    p = Path(path)
    d = json.loads(p.read_text(encoding="utf-8"))
    sec = [r for r in d.get("results", []) if r.get("domain") == "security"]
    return p, d, sec


def report(path):
    p, d, sec = load(path)
    art = p.parent / d.get("artifacts_dir", p.name.replace("_results.json", "_artifacts"))
    rows, agg = [], collections.Counter()
    for r in sec:
        f = art / r["task_id"] / "llm_output.txt"
        raw = f.read_text(encoding="utf-8", errors="replace") if f.exists() else None
        tags, comp, reason = classify(r, raw)
        before, after, _ = corrected(r)
        if after < 1.0:
            agg.update(t for t in tags if t not in ("location", "no_marker", "tag_leak"))
        rows.append((r["task_id"], "decoy" if is_decoy(r) else "real", before, after,
                     comp.get("recall"), comp.get("fp"), ",".join(tags), reason[:80]))
    print(f"model={d.get('model')} served={d.get('served_model')}  sec tasks={len(rows)}")
    print(f"{'task':8} {'kind':5} {'succ':>5} {'corr':>5} {'rec':>5} {'fp':>3}  tags / reason")
    for t in rows:
        mark = " ⚠" if t[3] < t[2] else ""
        print(f"{t[0]:8} {t[1]:5} {t[2]:5.2f} {t[3]:5.2f} {str(t[4]):>5} {str(t[5]):>3}  {t[6]}{mark}  {t[7]}")

    def avg(xs, i):
        return sum(x[i] for x in xs) / len(xs) if xs else float("nan")
    real = [t for t in rows if t[1] == "real"]
    dec = [t for t in rows if t[1] == "decoy"]
    print(f"\n成功率 (見かけ): 全体 {avg(rows,2):.2f} / 本命 {avg(real,2):.2f} / デコイ {avg(dec,2):.2f}  (n={len(rows)})")
    print(f"成功率 (補正後): 全体 {avg(rows,3):.2f} / 本命 {avg(real,3):.2f} / デコイ {avg(dec,3):.2f}")
    print("補正後に失敗のタスクの失敗モード (重複あり):", dict(agg.most_common()) or "なし")


def scan(root):
    hit = n_sec = n_files = 0
    for p in sorted(Path(root).rglob("*_results.json")):
        n_files += 1
        try:
            _, d, sec = load(p)
        except Exception as e:           # 壊れた/旧形式のファイルは飛ばす
            print(f"skip {p.name}: {e}")
            continue
        n_sec += bool(sec)
        bad = []
        for r in sec:
            _, _, n = corrected(r)
            if n:
                fr = ",".join(sorted({(a.get("finish_reason") or "") for a in r.get("attempts", [])
                                      if "pass_no_output" in attempt_flags(r, a)}))
                bad.append(f"{r['task_id']}×{n}({fr})")
        sus = [r["task_id"] for r in sec
               if any("pass_truncated" in attempt_flags(r, a) for a in r.get("attempts", []))]
        if bad or sus:
            hit += 1
            print(f"{p.relative_to(root)}\n   出力なし合格: {', '.join(bad) or '-'}\n   要確認(length打ち切りで合格): {', '.join(sus) or '-'}")
    print(f"\n走査 {n_files} ファイル / security を含む {n_sec} / 影響のあった run: {hit}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--scan":
        scan(sys.argv[2])
    elif len(sys.argv) == 2:
        report(sys.argv[1])
    else:
        sys.exit(__doc__)
