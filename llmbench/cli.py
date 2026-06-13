"""llmbench CLI.

使用例:
    llmbench list-tasks
    llmbench run --model local-ollama
    llmbench run --model local-openai --tasks t001,t003 --lang ja
    llmbench validate          # gold/brokenモックで自己検証
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from .runner import BenchmarkRunner, save_run
from .tasks import load_tasks


def _load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"config not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--tasks-dir", default="tasks")
    parser.add_argument(
        "--tasks", default=None,
        help="カンマ区切りのタスクID (例: t001,t003)。省略時は全タスク",
    )


def cmd_list_tasks(args) -> int:
    tasks = load_tasks(Path(args.tasks_dir))
    for t in tasks:
        print(f"{t.task_id}  [{t.difficulty:6s}]  {t.title}  ({len(t.files)} files)")
    print(f"total: {len(tasks)}")
    return 0


def cmd_run(args) -> int:
    config = _load_config(args.config)
    if args.lang:
        config.setdefault("run", {})["issue_lang"] = args.lang
    runner = BenchmarkRunner(config, Path(args.tasks_dir))
    only = args.tasks.split(",") if args.tasks else None
    run = runner.run(
        args.model, only_tasks=only,
        runs=args.runs, sample_temp=args.sample_temp,
    )
    json_path, md_path = save_run(run, Path(args.output))
    print()
    print(f"Resolved率   : {run.resolved_rate * 100:.1f}%")
    if run.multi_run:
        print(f"平均成功率   : {run.avg_success_rate * 100:.1f}% (×{run.runs}試行)")
        print(f"平均pass@{run.runs}  : {run.avg_pass_at_k * 100:.1f}%")
    print(f"品質平均     : {run.avg_quality_resolved:.1f}/100 (resolvedのみ)")
    print(f"Combined平均 : {run.avg_combined:.1f}/100")
    print(f"結果: {json_path}")
    print(f"レポート: {md_path}")
    return 0


def cmd_compare(args) -> int:
    """複数の results.json を横断比較するレポートを生成する."""
    from .compare import load_results, save_comparison

    paths = args.results
    if len(paths) < 2:
        print("⚠️  比較には2つ以上の results.json を推奨します。", file=sys.stderr)
    runs = load_results(paths)
    out = save_comparison(runs, Path(args.output), name=args.name)
    print(f"比較レポート: {out}")
    return 0


def cmd_validate(args) -> int:
    """gold/brokenモックで全パイプラインを自己検証する."""
    config = _load_config(args.config)
    config.setdefault("models", {})
    config["models"]["mock-gold"] = {"type": "mock", "mode": "gold"}
    config["models"]["mock-broken"] = {"type": "mock", "mode": "broken"}
    runner = BenchmarkRunner(config, Path(args.tasks_dir))
    only = args.tasks.split(",") if args.tasks else None

    print("=== mock-gold (全タスクresolvedになるべき) ===")
    gold = runner.run("mock-gold", only_tasks=only)
    print("\n=== mock-broken (全タスクfailになるべき) ===")
    broken = runner.run("mock-broken", only_tasks=only)

    n = len(gold.results)
    ok_gold = sum(r.resolved for r in gold.results)
    ok_broken = sum(not r.resolved for r in broken.results)
    print(f"\ngold  : {ok_gold}/{n} resolved (期待: {n}/{n})")
    print(f"broken: {ok_broken}/{n} failed   (期待: {n}/{n})")
    print(f"gold combined平均: {gold.avg_combined:.1f} (期待: >50)")
    print(f"broken combined平均: {broken.avg_combined:.1f} (期待: 0)")
    passed = ok_gold == n and ok_broken == n and broken.avg_combined == 0
    print("VALIDATION:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="llmbench",
        description="ローカルLLM向け 機能正確性+品質 ベンチマーク",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-tasks", help="タスク一覧を表示")
    _common_args(p_list)
    p_list.set_defaults(fn=cmd_list_tasks)

    p_run = sub.add_parser("run", help="ベンチマーク実行")
    _common_args(p_run)
    p_run.add_argument("--model", required=True, help="config.yamlのモデル名")
    p_run.add_argument("--lang", choices=["en", "ja"], default=None,
                       help="issue言語 (configを上書き)")
    p_run.add_argument("--output", default="results", help="結果出力先")
    p_run.add_argument(
        "--runs", type=int, default=None,
        help="各タスクの試行回数 (>1 で pass@k計測。既定: run.runs または1)",
    )
    p_run.add_argument(
        "--sample-temp", type=float, default=None, dest="sample_temp",
        help="複数試行時のサンプリング温度 (既定: configのrun.sample_temp または0.8)",
    )
    p_run.set_defaults(fn=cmd_run)

    p_cmp = sub.add_parser("compare", help="複数 results.json を横断比較")
    p_cmp.add_argument("results", nargs="+", help="比較する results.json (2つ以上)")
    p_cmp.add_argument("--output", default="results", help="比較レポート出力先")
    p_cmp.add_argument("--name", default="comparison", help="出力名プレフィックス")
    p_cmp.set_defaults(fn=cmd_compare)

    p_val = sub.add_parser("validate", help="モックで自己検証")
    _common_args(p_val)
    p_val.set_defaults(fn=cmd_validate)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
