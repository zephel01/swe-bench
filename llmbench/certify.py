"""tier合格制による「使えるライン」判定.

results.json (runner出力) を読み、難易度を tier(L1-L7) にマップして、
tierごとの平均成功率・平均combinedが gate を満たすかを **累積** で評価する。
モデルの到達レベル (= gateを満たした最上位tier) を返す。

- L4 (expert) gate = **使えるライン**: 監督付きで実務投入できる。
- 単体スクリプトとしても動く (stdlib のみ。llmbench本体に非依存):
    python3 certify.py results/<stamp>_<model>_results.json
- llmbench に組み込む場合は llmbench/certify.py として配置し、
  report.py / compare.py から `certify()` / `render_certificate_md()` を呼ぶ。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 難易度 -> tier。既存の easy/medium/hard と新規 expert/frontier/architect/grandmaster を対応づける。
DIFFICULTY_TO_TIER = {
    "easy": "L1",
    "medium": "L2",
    "hard": "L3",
    "expert": "L4",
    "frontier": "L5",
    "architect": "L6",
    "grandmaster": "L7",
}

TIER_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]

TIER_LABEL = {
    "L1": "L1 easy",
    "L2": "L2 medium",
    "L3": "L3 hard",
    "L4": "L4 expert (使えるライン)",
    "L5": "L5 frontier",
    "L6": "L6 architect",
    "L7": "L7 grandmaster (天井評価)",
}

# gate: そのtierのタスク平均が満たすべき下限。
# min_success は pass@1 平均 (success_rate)、min_combined は combined 平均。
DEFAULT_GATES = {
    "L1": {"min_success": 0.90, "min_combined": 0.0},
    "L2": {"min_success": 0.85, "min_combined": 0.0},
    "L3": {"min_success": 0.75, "min_combined": 60.0},
    "L4": {"min_success": 0.60, "min_combined": 55.0},
    "L5": {"min_success": 0.40, "min_combined": 0.0},
    # L6 (architect): Phase 3 較正で確定 (ornith 9B/35B ×5run, 2026-06-26)。
    "L6": {"min_success": 0.60, "min_combined": 58.0},
    # L7 (grandmaster): 暫定値。天井評価用 (t061-t100)。
    # 実モデル較正 (フロンティア級モデル ×5run 想定) で確定するまでの仮ゲート。
    "L7": {"min_success": 0.35, "min_combined": 55.0},
}

# 到達レベルの解釈 (レポート用の一言)。
LEVEL_VERDICT = {
    None: "L1未達。基本的なバグ修正も安定せず、実務利用は不可。",
    "L1": "おもちゃ級は確実だが、実務の単純バグはまだ不安定。",
    "L2": "仕様準拠の単純作業は任せられる。",
    "L3": "実務の単純〜中級バグは任せられる。",
    "L4": "✅ 使えるライン到達。監督付きで実務投入できる。",
    "L5": "フロンティア級。複雑案件も補助付きで任せられる。",
    "L6": "アーキテクト級。リポジトリ規模の診断・設計判断まで任せられる。",
    "L7": "グランドマスター級。天井評価帯まで到達 — 現行タスク群では頭打ちが見えない水準。",
}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _task_success(t: dict) -> float:
    """success_rate を取得。runs=1 の旧形式なら resolved を 0/1 に。"""
    if "success_rate" in t and t["success_rate"] is not None:
        return float(t["success_rate"])
    return 1.0 if t.get("resolved") else 0.0


def aggregate_by_tier(results: list[dict]) -> dict[str, dict]:
    """tierごとに success_rate / combined の平均と件数を集計する。"""
    buckets: dict[str, dict[str, list]] = {}
    for t in results:
        tier = DIFFICULTY_TO_TIER.get(t.get("difficulty"))
        if tier is None:
            continue
        b = buckets.setdefault(tier, {"success": [], "combined": [], "ids": []})
        b["success"].append(_task_success(t))
        b["combined"].append(float(t.get("combined", 0.0)))
        b["ids"].append(t.get("task_id"))
    out: dict[str, dict] = {}
    for tier, b in buckets.items():
        out[tier] = {
            "n": len(b["ids"]),
            "mean_success": _mean(b["success"]),
            "mean_combined": _mean(b["combined"]),
            "task_ids": b["ids"],
        }
    return out


def certify(results: list[dict], gates: dict | None = None) -> dict:
    """tier集計 -> gate判定 -> 到達レベル.

    戻り値: {achieved_level, verdict, tiers:[{tier,n,mean_success,
    mean_combined,gate_pass,measured}], gates}
    achieved_level は「測定済みかつ下位を含め連続して gate を満たした最上位tier」。
    タスクが無い (未測定) tier は判定をスキップし、合否のブロックもしない。
    """
    gates = gates or DEFAULT_GATES
    agg = aggregate_by_tier(results)

    rows = []
    achieved = None
    broken = False  # 一度 gate を落としたらそれ以上は認証しない
    for tier in TIER_ORDER:
        g = gates[tier]
        if tier not in agg:
            rows.append({
                "tier": tier, "measured": False, "n": 0,
                "mean_success": None, "mean_combined": None,
                "gate_pass": None,
                "gate": g,
            })
            continue
        a = agg[tier]
        passed = (
            a["mean_success"] >= g["min_success"]
            and a["mean_combined"] >= g["min_combined"]
        )
        rows.append({
            "tier": tier, "measured": True, "n": a["n"],
            "mean_success": a["mean_success"],
            "mean_combined": a["mean_combined"],
            "gate_pass": passed,
            "gate": g,
            "task_ids": a["task_ids"],
        })
        if not broken:
            if passed:
                achieved = tier
            else:
                broken = True

    # 非累積判定: 各tierを独立に評価する (下位tierの取りこぼしでブロックしない)。
    measured = [r for r in rows if r["measured"]]
    independent_pass = [r["tier"] for r in measured if r["gate_pass"]]
    l4 = next((r for r in rows if r["tier"] == "L4"), None)
    usable_line = bool(l4 and l4["measured"] and l4["gate_pass"])

    return {
        "achieved_level": achieved,          # 累積 (下位から連続合格した最上位)
        "verdict": LEVEL_VERDICT.get(achieved, ""),
        "usable_line": usable_line,          # 主判定: L4を独立に合格したか
        "independent_pass": independent_pass,  # 独立に合格した全tier
        "tiers": rows,
        "gates": gates,
    }


def render_certificate_md(cert: dict, model: str = "") -> str:
    lines = []
    head = f"## 🎓 認証 (使えるライン判定){f': {model}' if model else ''}"
    lines.append(head)

    # 主判定: 使えるライン = L4 を独立に合格したか (非累積)。
    usable = cert.get("usable_line")
    usable_txt = "✅ 使えるライン到達" if usable else "❌ 使えるライン未到達"
    lines.append(f"\n**{usable_txt}** (L4 expert を独立に合格){'' if usable else ''}")

    # 副判定: 累積到達レベル (下位tierも連続合格＝一貫性の指標)。
    lvl = cert["achieved_level"]
    lvl_txt = TIER_LABEL.get(lvl, "なし (L1未達)")
    indep = cert.get("independent_pass", [])
    lines.append(
        f"参考: 累積到達レベル **{lvl_txt}** / 独立合格tier: "
        f"{', '.join(indep) if indep else 'なし'}\n"
    )

    lines.append("| Tier | 独立判定 | タスク数 | 平均成功率 | 平均combined | gate(成功率/combined) |")
    lines.append("|---|---|---|---|---|---|")
    for r in cert["tiers"]:
        g = r["gate"]
        gate_s = f"≥{g['min_success']:.0%} / ≥{g['min_combined']:.0f}"
        if not r["measured"]:
            lines.append(f"| {r['tier']} | — 未測定 | 0 | – | – | {gate_s} |")
            continue
        mark = "✅合格" if r["gate_pass"] else "❌不合格"
        lines.append(
            f"| {r['tier']} | {mark} | {r['n']} | "
            f"{r['mean_success']:.0%} | {r['mean_combined']:.1f} | {gate_s} |"
        )
    lines.append(
        "\n> **使えるライン = L4 を独立に合格** (下位tierの取りこぼしに左右されない)。"
        " 累積到達レベルは『下位から連続して合格した最上位』で、一貫性の参考指標。"
        " L7(grandmaster)は天井評価帯 — gateは暫定値であり、実モデル較正で確定する。"
    )
    return "\n".join(lines)


def _load_results(path: Path) -> tuple[str, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("model", ""), data.get("results", [])


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 certify.py <results.json> [more.json ...]")
        return 1
    for arg in argv:
        model, results = _load_results(Path(arg))
        cert = certify(results)
        print(render_certificate_md(cert, model))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
