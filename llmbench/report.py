"""Markdownレポート生成."""

from __future__ import annotations

from . import usability


def _fmt_ruff(c: dict) -> str:
    issues = c.get("issues", 0)
    if issues == 0:
        return f"✅ 指摘なし ({c.get('loc', 0)} LOC)"
    rules = ", ".join(c.get("rules", [])) or "-"
    return (
        f"⚠️ {issues}件 / {c.get('loc', 0)} LOC "
        f"(密度 {c.get('density_per_100loc', 0)}/100行, rules: {rules})  "
        f"score={c.get('score', 0):.0f}"
    )


def _fmt_complexity(c: dict) -> str:
    rank = c.get("worst_cc_rank", "?")
    worst = c.get("worst_function") or "-"
    mi = c.get("maintainability_index", 0)
    line = (
        f"MI={mi:.0f}(保守性: 高いほど良い, 100満点) / "
        f"最大複雑度ランク={rank}(A=良い〜F=悪い) → "
        f"score={c.get('score', 0):.0f}(高いほど良い, 100満点)"
    )
    if worst != "-":
        line += f"  (最複雑: {worst})"
    return line


def _fmt_component(name: str, c: dict) -> str:
    if name == "ruff":
        return _fmt_ruff(c)
    if name == "complexity":
        return _fmt_complexity(c)
    # 汎用フォールバック
    detail = ", ".join(f"{k}={v}" for k, v in c.items() if k != "enabled")
    return detail


def _status_icon(r) -> str:
    return "✅" if r.resolved else "❌"


def _tier_cell(r) -> str:
    return usability.TIER_LABEL.get(r.usability_tier, "—")


def _usability_section(run) -> list[str]:
    """usability判定セクション (ティア集計・難易度×ティア・総合判定)."""
    overall, by_diff = usability.aggregate(run.results)
    n = len(run.results)
    lines = ["## 🧭 usability判定（実際どれくらい任せられるか）", ""]
    for t in usability.TIERS:
        cnt = overall.get(t, 0)
        pct = (cnt / n * 100) if n else 0
        lines.append(
            f"- {usability.TIER_LABEL[t]} **{cnt}/{n}** ({pct:.0f}%) "
            f"… {usability.TIER_DESC[t]}"
        )
    # 難易度×ティア マトリクス
    lines += ["", "| 難易度 | 🟢 自律 | 🟡 補助 | 🔴 不可 |", "|---|---|---|---|"]
    for diff in ("easy", "medium", "hard"):
        if diff not in by_diff:
            continue
        c = by_diff[diff]
        lines.append(
            f"| {diff} | {c.get('autonomous', 0)} | "
            f"{c.get('assisted', 0)} | {c.get('unusable', 0)} |"
        )
    # 総合判定 (難易度ごとの最多ティア)
    verdicts = []
    for diff in ("easy", "medium", "hard"):
        if diff not in by_diff:
            continue
        top = by_diff[diff].most_common(1)[0][0]
        verdicts.append(f"{diff}={usability.TIER_LABEL[top]}")
    if verdicts:
        lines += ["", f"> 総合: {' / '.join(verdicts)}"]
    lines.append("")
    return lines


def render_markdown(run) -> str:
    n = len(run.results)
    n_resolved = sum(r.resolved for r in run.results)
    multi = getattr(run, "multi_run", False)
    lines = [
        f"# llmbench レポート: {run.model}",
        "",
        f"Issue言語: `{run.issue_lang}` / タスク数: {n}"
        + (f" / 試行: ×{run.runs}" if multi else ""),
        "",
        "## サマリ",
        "",
        "| 指標 | 値 |",
        "|---|---|",
        f"| ✅ Resolved率 | **{run.resolved_rate * 100:.1f}%** "
        f"({n_resolved}/{n}) |",
    ]
    if multi:
        lines += [
            f"| 🎲 平均成功率 (×{run.runs}) | **{run.avg_success_rate * 100:.1f}%** |",
            f"| 🔁 平均pass@{run.runs} | **{run.avg_pass_at_k * 100:.1f}%** |",
        ]
    lines += [
        f"| 🏅 品質平均 (resolvedのみ) | **{run.avg_quality_resolved:.1f} / 100** |",
        f"| 🎯 Combined平均 | **{run.avg_combined:.1f} / 100** |",
        "",
    ]
    # usability判定 (サマリ直下)
    lines += _usability_section(run)

    if run.artifacts_dirname:
        lines += [
            f"> 📂 生成物 (LLM生出力・生成コード・pytest出力) は "
            f"`{run.artifacts_dirname}/<task_id>/` に保存。",
            "> パース失敗やテスト失敗の原因はそこで確認できる。",
            "",
        ]

    # タスク別結果
    rel_h = "| 信頼性 " if multi else ""
    rel_sep = "---|" if multi else ""
    lines += [
        "## タスク別結果",
        "",
        f"| | Task | 難易度 | 判定 {rel_h}| 生成ファイル | Quality | Combined "
        "| 生成時間 | tok/s | 備考 |",
        f"|---|---|---|---|{rel_sep}---|---|---|---|---|---|",
    ]
    for r in run.results:
        files = ", ".join(f"`{f}`" for f in r.changed_files) or "—"
        note = r.fail_reason or (r.parse_error if not r.parse_ok else "") or "—"
        rel_c = (
            f"| {r.n_pass}/{r.runs} (p@{r.runs}={r.pass_at_k:.2f}) " if multi else ""
        )
        lines.append(
            f"| {_status_icon(r)} | {r.task_id} | {r.difficulty} "
            f"| {_tier_cell(r)} {rel_c}"
            f"| {files} "
            f"| {r.quality_score:.0f} | {r.combined:.0f} "
            f"| {r.latency_sec:.1f}s "
            f"| {r.tokens_per_sec if r.tokens_per_sec else '-'} "
            f"| {note} |"
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

    # タスク別の詳細 (生成物・品質内訳)
    lines += ["", "## タスク別詳細", ""]
    for r in run.results:
        lines.append(f"### {_status_icon(r)} {r.task_id} — {r.title}")
        lines.append("")
        lines.append(
            f"- 難易度: {r.difficulty} / "
            f"判定: {'RESOLVED' if r.resolved else 'FAILED'}"
            + (f" ({r.fail_reason})" if r.fail_reason else "")
            + f" / usability: {usability.TIER_LABEL.get(r.usability_tier, '—')}"
        )
        if multi:
            lines.append(
                f"- 信頼性: 成功 {r.n_pass}/{r.runs} "
                f"(pass@1={r.pass_at_1:.2f}, pass@{r.runs}={r.pass_at_k:.2f})"
            )
        if not r.parse_ok:
            lines.append(f"- ⚠️ パース失敗: {r.parse_error or '不明'}")
        if r.changed_files:
            lines.append(f"- 生成ファイル: {', '.join(r.changed_files)}")
        if run.artifacts_dirname:
            lines.append(
                f"- 生成物: `{run.artifacts_dirname}/{r.task_id}/`"
            )
        # 品質内訳
        for name, comp in r.quality_components.items():
            if not comp.get("enabled"):
                continue
            lines.append(f"- {name}: {_fmt_component(name, comp)}")
        lines.append("")

    return "\n".join(lines) + "\n"
