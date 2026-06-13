"""複数の results.json を横断比較するレポートを生成する.

参照モデル (強い/弱い) と並べることで、ローカルモデルのスコアを
「どの位置にあるか」相対的に解釈できるようにする (アンカー)。
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def load_results(paths: list[str | Path]) -> list[dict]:
    """results.json 群を読み込む. ファイル名でなくmodel名で識別する."""
    runs = []
    for p in paths:
        p = Path(p)
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_path"] = p.name
        runs.append(d)
    return runs


def _avg_tps(results: list[dict]) -> float | None:
    vals = [r.get("tokens_per_sec") for r in results if r.get("tokens_per_sec")]
    return sum(vals) / len(vals) if vals else None


def _task_index(runs: list[dict]) -> dict[str, dict]:
    """task_id -> {difficulty, title} (最初に見つかったものを採用)."""
    idx: dict[str, dict] = {}
    for run in runs:
        for r in run.get("results", []):
            tid = r["task_id"]
            if tid not in idx:
                idx[tid] = {
                    "difficulty": r.get("difficulty", ""),
                    "title": r.get("title", ""),
                }
    return idx


def render_comparison(runs: list[dict]) -> str:
    if not runs:
        return "# モデル比較\n\n(結果がありません)\n"

    # モデルごとのサマリを取り出し、combined降順でランキング
    rows = []
    for run in runs:
        s = run.get("summary", {})
        rows.append({
            "model": run.get("model", run.get("_path", "?")),
            "lang": run.get("issue_lang", "?"),
            "runs": s.get("runs", 1),
            "resolved": s.get("resolved_rate", 0.0),
            "success": s.get("avg_success_rate"),
            "passk": s.get("avg_pass_at_k"),
            "quality": s.get("avg_quality_resolved", 0.0),
            "combined": s.get("avg_combined", 0.0),
            "tps": _avg_tps(run.get("results", [])),
            "usability": s.get("usability", {}),
            "results": {r["task_id"]: r for r in run.get("results", [])},
        })
    rows.sort(key=lambda x: x["combined"], reverse=True)
    best = rows[0]["combined"] or 1.0
    any_multi = any(r["runs"] > 1 for r in rows)

    lines = [
        "# 🆚 モデル比較レポート",
        "",
        f"対象モデル: {len(rows)} / 生成: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## ランキング（Combined平均 降順）",
        "",
    ]
    # ヘッダ
    head = "| # | モデル | 言語 | Resolved "
    sep = "|---|---|---|---|"
    if any_multi:
        head += "| 成功率 | pass@k "
        sep += "---|---|"
    head += "| 品質 | Combined | 相対 | tok/s |"
    sep += "---|---|---|---|"
    lines += [head, sep]
    for i, r in enumerate(rows, 1):
        rel = r["combined"] / best * 100 if best else 0
        mid = ""
        if any_multi:
            sc = f"{r['success'] * 100:.1f}%" if r["success"] is not None else "—"
            pk = f"{r['passk'] * 100:.1f}%" if r["passk"] is not None else "—"
            mid = f"| {sc} | {pk} "
        tps = f"{r['tps']:.1f}" if r["tps"] else "—"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
        lines.append(
            f"| {i}{medal} | **{r['model']}** | {r['lang']} "
            f"| {r['resolved'] * 100:.1f}% {mid}"
            f"| {r['quality']:.1f} | {r['combined']:.1f} "
            f"| {rel:.0f}% | {tps} |"
        )

    # usabilityティア比較
    lines += ["", "## usabilityティア比較", "",
              "| モデル | 🟢 自律 | 🟡 補助 | 🔴 不可 |", "|---|---|---|---|"]
    for r in rows:
        u = r["usability"] or {}
        lines.append(
            f"| {r['model']} | {u.get('autonomous', 0)} "
            f"| {u.get('assisted', 0)} | {u.get('unusable', 0)} |"
        )

    # タスク別マトリクス (セル = combined, 行内ベストを太字)
    idx = _task_index(runs)
    lines += ["", "## タスク別 Combined マトリクス", "",
              "各セルはそのタスクの Combined。行内の最高値を **太字**。", ""]
    header = "| Task | 難易度 | " + " | ".join(r["model"] for r in rows) + " |"
    lines += [header, "|---|---|" + "---|" * len(rows)]
    for tid in sorted(idx):
        diff = idx[tid]["difficulty"]
        cells = []
        present = [r["results"].get(tid) for r in rows]
        vals = [p.get("combined") if p else None for p in present]
        bestval = max([v for v in vals if v is not None], default=None)
        for v in vals:
            if v is None:
                cells.append("—")
            elif bestval is not None and v == bestval:
                cells.append(f"**{v:.0f}**")
            else:
                cells.append(f"{v:.0f}")
        lines.append(f"| {tid} | {diff} | " + " | ".join(cells) + " |")

    lines += ["", "> 相対 = 各モデルのCombined ÷ 最良モデルのCombined。",
              "> 参照モデル(強/弱)を併置すると、ローカルモデルの位置が読み取れる。"]
    return "\n".join(lines) + "\n"


def save_comparison(
    runs: list[dict], output_dir: Path, name: str = "comparison"
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = output_dir / f"{name}_{stamp}.md"
    out.write_text(render_comparison(runs), encoding="utf-8")
    return out
