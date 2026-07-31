"""複数の results.json を横断比較するレポートを生成する.

参照モデル (強い/弱い) と並べることで、ローカルモデルのスコアを
「どの位置にあるか」相対的に解釈できるようにする (アンカー)。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .env import EXEC_LABEL, format_summary


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


def _run_tps(run: dict) -> float | None:
    """summary の値を優先し、無ければ results[] から平均する."""
    s = (run.get("summary") or {}).get("tokens_per_sec")
    if s:
        return float(s)
    return _avg_tps(run.get("results", []))


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


def _device_label(env: dict) -> str:
    """その実行で実際に使われたデバイス名 (無ければ搭載GPU/CPU)."""
    backend = env.get("backend") or {}
    launch = backend.get("launch") or {}
    if launch.get("device_name"):
        return str(launch["device_name"])
    inf = (backend.get("gpu_usage") or {}).get("inference") or {}
    real = [g.get("name") for g in inf.get("gpus", [])
            if not g.get("context_only")]
    if real:
        return " + ".join(str(n) for n in real)
    host = env.get("host") or {}
    gpus = host.get("gpu") or []
    if gpus:
        return str(gpus[0].get("name", "?"))
    return str(host.get("cpu") or "—")


def _compute_label(env: dict) -> str:
    backend = env.get("backend") or {}
    rt = backend.get("runtime") or {}
    return str(rt.get("compute") or backend.get("kind") or "—")


def _bench_conditions(env: dict) -> dict:
    """tok/s の比較可否を左右する推論条件 (ここが揃って初めて比較が成立する)."""
    backend = env.get("backend") or {}
    launch = backend.get("launch") or {}
    return {
        "量子化": backend.get("quantization"),
        "-ngl": launch.get("n_gpu_layers"),
        "n_ctx": launch.get("n_ctx") or backend.get("n_ctx"),
        "並列": launch.get("parallel") or backend.get("parallel_slots"),
    }


def _fmt_conditions(cond: dict) -> str:
    parts = [f"{k} {v}" for k, v in cond.items() if v is not None]
    return " / ".join(parts) or "—"


def _env_signature(env: dict) -> str:
    """同一環境で測ったかの判定キー.

    ホストのスペックだけでは足りない。**同じマシンでも**使ったデバイスや
    計算バックエンドが違えば別環境なので (実機: 1台に RTX 5090 / RTX 3090 /
    Radeon 8060S が同居し、CUDA / ROCm / Vulkan を切り替えて測る)、
    実際に測った条件までキーに含める。
    """
    host = env.get("host") or {}
    backend = env.get("backend") or {}
    gpu = ",".join(str(g.get("name", "")) for g in (host.get("gpu") or []))
    cond = _bench_conditions(env)
    return "|".join(str(x) for x in (
        env.get("execution", ""), host.get("cpu", ""), gpu,
        host.get("ram_gb", ""), backend.get("kind", ""),
        _compute_label(env), _device_label(env),
        cond["量子化"], cond["-ngl"], cond["n_ctx"], cond["並列"],
    ))


def is_hardware_comparison(rows: list[dict]) -> bool:
    """「同じモデルを別のハードで測った」比較かを判定する.

    このとき tok/s は**主役**であって「環境が違うから比較不可」ではない。
    逆にモデルが混在していれば従来どおりモデル比較として扱う。
    """
    envs = [r for r in rows if r.get("env")]
    if len(envs) < 2:
        return False
    models = {r["model"] for r in envs}
    sigs = {_env_signature(r["env"]) for r in envs}
    return len(models) == 1 and len(sigs) > 1


def _hardware_section(rows: list[dict]) -> list[str]:
    """ハードウェア比較モード: モデル固定で tok/s を主役に出す."""
    envs = [r for r in rows if r.get("env")]
    ranked = sorted(envs, key=lambda r: r["tps"] or 0, reverse=True)
    best = ranked[0]["tps"] or 0
    lines = [
        "", "## 🖥 ハードウェア比較（モデル固定）", "",
        f"モデル `{ranked[0]['model']}` を {len(envs)} 環境で測定。"
        "速度が比較の主役なので tok/s 降順で並べます。", "",
        "| # | デバイス | 計算バックエンド | tok/s | 相対 | 推論条件 |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(ranked, 1):
        env = r["env"]
        tps = r["tps"]
        rel = f"{tps / best * 100:.0f}%" if tps and best else "—"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
        lines.append(
            f"| {i}{medal} | **{_device_label(env)}** | {_compute_label(env)} "
            f"| {tps:.1f} | {rel} "
            f"| {_fmt_conditions(_bench_conditions(env))} |"
            if tps is not None else
            f"| {i}{medal} | **{_device_label(env)}** | {_compute_label(env)} "
            f"| — | — | {_fmt_conditions(_bench_conditions(env))} |"
        )

    # ★ 速度比較が成立するのは推論条件が揃っているときだけ。
    #   実測で -ngl 0 (CPU実行) と -ngl 99 を比べて結論が逆転した事故があった。
    conds = [_bench_conditions(r["env"]) for r in envs]
    differing = sorted({k for k in conds[0]
                        if len({str(c.get(k)) for c in conds}) > 1})
    if differing:
        lines += ["", f"> ⚠️ **推論条件が揃っていません（{', '.join(differing)}）。**"
                      "この状態の tok/s 差はハードの差ではありません。"
                      "特に `-ngl` が 0 の実行は GPU を使っていません。"]
    else:
        lines += ["", "> ✅ 推論条件（量子化 / -ngl / n_ctx / 並列）が全環境で"
                      "一致しています。tok/s の差はハードとバックエンドの差です。"]
    if len(envs) < len(rows):
        lines += ["", "> ⚠️ 実行環境が記録されていない results は表から除外して"
                      "います (旧バージョンで生成)。"]
    lines.append("")
    return lines


def _env_compare_section(rows: list[dict]) -> list[str]:
    """モデルごとの実行環境を並べ、tok/s の比較可否を明示する."""
    envs = [r for r in rows if r.get("env")]
    if not envs:
        return ["", "> ⚠️ 実行環境が記録されていない results があります "
                    "(旧バージョンで生成)。tok/s の比較には注意。"]
    # 同一モデル × 別ハード なら「比較不可」ではなく「ハード比較」が目的
    if is_hardware_comparison(rows):
        return _hardware_section(rows)
    lines = ["", "## 🖥 実行環境", "",
             "| モデル | 実行形態 | ハード / 推論構成 |", "|---|---|---|"]
    for r in rows:
        env = r.get("env") or {}
        if not env:
            lines.append(f"| {r['model']} | — | (記録なし) |")
            continue
        label = EXEC_LABEL.get(env.get("execution", ""), env.get("execution", "?"))
        lines.append(
            f"| {r['model']} | {label} | {format_summary(env) or '—'} |"
        )
    sigs = {_env_signature(r["env"]) for r in envs}
    local = [r for r in envs if (r["env"].get("execution") == "local")]
    if len(sigs) > 1:
        lines += ["", "> ⚠️ **測定環境が揃っていません**。tok/s は環境依存なので"
                      "速度の直接比較は不可 (品質・Resolvedの比較は有効)。"]
    elif local and len(local) == len(envs):
        lines += ["", "> ✅ 全モデルが同一環境で測定されています "
                      "(tok/s の直接比較が可能)。"]
    if len(envs) < len(rows):
        lines += ["", "> ⚠️ 実行環境が記録されていない results があります "
                      "(旧バージョンで生成)。"]
    lines.append("")
    return lines


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
            "tps": _run_tps(run),
            "usability": s.get("usability", {}),
            "env": run.get("environment") or {},
            "results": {r["task_id"]: r for r in run.get("results", [])},
        })
    rows.sort(key=lambda x: x["combined"], reverse=True)
    best = rows[0]["combined"] or 1.0
    any_multi = any(r["runs"] > 1 for r in rows)

    # 同一モデル × 別ハードの比較では、モデル名が全行同じで区別できないので
    # 表示ラベルをデバイス名に切り替える。
    hardware = is_hardware_comparison(rows)
    for r in rows:
        env = r.get("env") or {}
        r["label"] = (
            f"{_device_label(env)} ({_compute_label(env)})" if hardware and env
            else r["model"]
        )

    lines = [
        "# 🆚 ハードウェア比較レポート" if hardware else "# 🆚 モデル比較レポート",
        "",
        (f"モデル `{rows[0]['model']}` / 環境: {len(rows)}"
         if hardware else f"対象モデル: {len(rows)}")
        + f" / 生成: {time.strftime('%Y-%m-%d %H:%M')}",
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
            f"| {i}{medal} | **{r['label']}** | {r['lang']} "
            f"| {r['resolved'] * 100:.1f}% {mid}"
            f"| {r['quality']:.1f} | {r['combined']:.1f} "
            f"| {rel:.0f}% | {tps} |"
        )

    # 実行環境の併記 (tok/s は測定環境が違うと比較できないため必須)
    lines += _env_compare_section(rows)

    # usabilityティア比較
    lines += ["", "## usabilityティア比較", "",
              "| モデル | 🟢 自律 | 🟡 補助 | 🔴 不可 |", "|---|---|---|---|"]
    for r in rows:
        u = r["usability"] or {}
        lines.append(
            f"| {r['label']} | {u.get('autonomous', 0)} "
            f"| {u.get('assisted', 0)} | {u.get('unusable', 0)} |"
        )

    # タスク別マトリクス (セル = combined, 行内ベストを太字)
    idx = _task_index(runs)
    lines += ["", "## タスク別 Combined マトリクス", "",
              "各セルはそのタスクの Combined。行内の最高値を **太字**。", ""]
    header = "| Task | 難易度 | " + " | ".join(r["label"] for r in rows) + " |"
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
