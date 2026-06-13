"""Markdownレポート生成."""

from __future__ import annotations


def render_markdown(run) -> str:
    lines = [
        f"# llmbench レポート: {run.model}",
        "",
        f"- Issue言語: {run.issue_lang}",
        f"- タスク数: {len(run.results)}",
        f"- **Resolved率: {run.resolved_rate * 100:.1f}%**",
        f"- **品質平均 (resolvedのみ): {run.avg_quality_resolved:.1f}/100**",
        f"- **Combined平均: {run.avg_combined:.1f}/100**",
        "",
        "## タスク別結果",
        "",
        "| Task | 難易度 | Resolved | Quality | Combined "
        "| 生成時間(s) | tok/s | 失敗理由 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in run.results:
        lines.append(
            f"| {r.task_id} | {r.difficulty} "
            f"| {'O' if r.resolved else 'X'} "
            f"| {r.quality_score:.0f} | {r.combined:.0f} "
            f"| {r.latency_sec:.1f} "
            f"| {r.tokens_per_sec if r.tokens_per_sec else '-'} "
            f"| {r.fail_reason or '-'} |"
        )

    # 難易度別集計
    lines += ["", "## 難易度別", "",
              "| 難易度 | Resolved | 品質平均 |", "|---|---|---|"]
    for diff in ("easy", "medium", "hard"):
        rs = [r for r in run.results if r.difficulty == diff]
        if not rs:
            continue
        solved = sum(r.resolved for r in rs)
        qs = [r.quality_score for r in rs if r.resolved]
        avg_q = f"{sum(qs) / len(qs):.0f}" if qs else "-"
        lines.append(f"| {diff} | {solved}/{len(rs)} | {avg_q} |")

    lines += ["", "## 品質内訳 (タスク別)", ""]
    for r in run.results:
        if not r.quality_components:
            continue
        lines.append(f"### {r.task_id}")
        for name, comp in r.quality_components.items():
            if not comp.get("enabled"):
                continue
            detail = {k: v for k, v in comp.items() if k != "enabled"}
            lines.append(f"- {name}: {detail}")
        lines.append("")
    return "\n".join(lines) + "\n"
