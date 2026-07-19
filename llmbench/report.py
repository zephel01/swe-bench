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
    for diff in ("easy", "medium", "hard", "expert", "frontier", "architect", "grandmaster"):
        if diff not in by_diff:
            continue
        c = by_diff[diff]
        lines.append(
            f"| {diff} | {c.get('autonomous', 0)} | "
            f"{c.get('assisted', 0)} | {c.get('unusable', 0)} |"
        )
    # 難易度別の割合 (最頻ティアでの楽観的な丸めを避け、分布を明示)
    def _pct(c, key):
        tot = sum(c.values()) or 1
        return c.get(key, 0) / tot * 100

    lines += ["", "**難易度別の内訳（割合）**", ""]
    for diff in ("easy", "medium", "hard", "expert", "frontier", "architect", "grandmaster"):
        if diff not in by_diff:
            continue
        c = by_diff[diff]
        lines.append(
            f"- {diff}: 🟢自律 {_pct(c, 'autonomous'):.0f}% / "
            f"🟡補助 {_pct(c, 'assisted'):.0f}% / "
            f"🔴不可 {_pct(c, 'unusable'):.0f}%"
        )

    # 全体の保守的な推奨 (不可があれば自律と言い切らない)
    un = overall.get("unusable", 0)
    assisted = overall.get("assisted", 0)
    un_pct = (un / n * 100) if n else 0
    if un == 0 and assisted == 0:
        rec = "ほぼ自律で運用可"
    elif un_pct < 10:
        rec = f"おおむね自律。ただし🔴不可 {un}/{n} ({un_pct:.0f}%) は要注意"
    elif un_pct < 30:
        rec = f"補助つき運用が無難（🔴不可 {un}/{n} = {un_pct:.0f}%）"
    else:
        rec = f"このタスク群では限定的（🔴不可 {un}/{n} = {un_pct:.0f}%）"
    lines += ["", f"> 総合推奨: {rec}"]
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
        n_any = sum(1 for r in run.results if r.n_pass > 0)
        lines += [
            f"| 🎲 平均成功率 (pass@1, ×{run.runs}) | "
            f"**{run.avg_success_rate * 100:.1f}%** |",
            f"| 🔁 ≥1成功できたタスク | "
            f"**{run.solved_any_rate * 100:.1f}%** ({n_any}/{n}) |",
        ]
    lines += [
        f"| 🏅 品質平均 (resolvedのみ) | **{run.avg_quality_resolved:.1f} / 100** |",
        f"| 🎯 Combined平均 | **{run.avg_combined:.1f} / 100** |",
        "",
    ]
    if multi:
        lines += [
            "> 成功率 (pass@1) = 1回試行で通る期待値＝**信頼性の主指標**。"
            "≥1成功 = N回中1回でも通ったか（再試行込みの到達可能性）。",
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
            f"| {r.n_pass}/{r.runs} (成功率{r.success_rate * 100:.0f}%) "
            if multi else ""
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
    for diff in ("easy", "medium", "hard", "expert", "frontier", "architect", "grandmaster"):
        rs = [r for r in run.results if r.difficulty == diff]
        if not rs:
            continue
        solved = sum(r.resolved for r in rs)
        qs = [r.quality_score for r in rs if r.resolved]
        avg_q = f"{sum(qs) / len(qs):.0f}" if qs else "-"
        lines.append(f"| {diff} | {solved}/{len(rs)} | {avg_q} |")

    # ドメイン別集計 (コーディング以外の grader が混在する場合のみ)
    domains = [d for d in ("security", "general", "writing", "medical")
               if any(getattr(r, "domain", "code") == d for r in run.results)]
    if domains:
        _dlabel = {"security": "🛡️ security", "general": "📋 general",
                   "writing": "✍️ writing", "medical": "🩺 medical"}
        lines += ["", "## 🌐 ドメイン別 (コーディング以外)", "",
                  "| Domain | Resolved | 平均成功率 | 平均combined |", "|---|---|---|---|"]
        for d in domains:
            rs = [r for r in run.results if getattr(r, "domain", "code") == d]
            solved = sum(r.resolved for r in rs)
            sr = sum(r.success_rate for r in rs) / len(rs) * 100
            cb = sum(r.combined for r in rs) / len(rs)
            lines.append(
                f"| {_dlabel[d]} | {solved}/{len(rs)} | {sr:.0f}% | {cb:.1f} |"
            )

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
            anymark = "✓" if r.n_pass > 0 else "✗"
            lines.append(
                f"- 信頼性: 成功 {r.n_pass}/{r.runs} "
                f"（成功率 {r.success_rate * 100:.0f}% = pass@1） / "
                f"{r.runs}回中≥1成功: {anymark}"
            )
        if not r.parse_ok:
            lines.append(f"- ⚠️ パース失敗: {r.parse_error or '不明'}")
        if r.changed_files:
            lines.append(f"- 生成ファイル: {', '.join(r.changed_files)}")
        if run.artifacts_dirname:
            lines.append(
                f"- 生成物: `{run.artifacts_dirname}/{r.task_id}/`"
            )
        # 品質内訳 (複数試行では代表1試行の値である点を明記)
        if r.quality_components and any(
            c.get("enabled") for c in r.quality_components.values()
        ):
            if multi:
                lines.append(
                    f"- 品質内訳（下記は**代表1試行**の値。"
                    f"上のQuality {r.quality_score:.0f} は{r.runs}試行の平均）:"
                )
            for name, comp in r.quality_components.items():
                if not comp.get("enabled"):
                    continue
                prefix = "  - " if multi else "- "
                lines.append(f"{prefix}{name}: {_fmt_component(name, comp)}")
        lines.append("")

    return "\n".join(lines) + "\n"
