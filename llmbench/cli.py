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

from .clients.ollama import list_ollama_models
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
    parser.add_argument(
        "--with-l6", action="store_true", dest="with_l6",
        help="既定40問に加えて L6 (architect tier) の追加20問を含める",
    )
    parser.add_argument(
        "--l6-ledger", default="tasks_l6.jsonl", dest="l6_ledger",
        help="L6 追加台帳のファイル名 (tasks-dir 内。既定: tasks_l6.jsonl)",
    )
    parser.add_argument(
        "--with-l7", action="store_true", dest="with_l7",
        help="既定40問(+L6)に加えて L7 (grandmaster tier) の追加40問を含める",
    )
    parser.add_argument(
        "--l7-ledger", default="tasks_l7.jsonl", dest="l7_ledger",
        help="L7 追加台帳のファイル名 (tasks-dir 内。既定: tasks_l7.jsonl)",
    )
    parser.add_argument(
        "--only-l6", action="store_true", dest="only_l6",
        help="既定40問を除外し L6 (architect) の追加台帳だけを実行する",
    )
    parser.add_argument(
        "--only-l7", action="store_true", dest="only_l7",
        help="既定40問を除外し L7 (grandmaster) の追加台帳だけを実行する",
    )


def _ledgers(args) -> list[str]:
    """実行対象の台帳リストを決める.

    優先規則:
      - `--only-l6` / `--only-l7` のいずれかが指定されたら「only モード」。
        既定台帳 tasks.jsonl を除外し、要求された tier 台帳だけを対象にする。
      - only モードでも `--with-l6`/`--with-l7` は同 tier の追加要求として尊重する
        (実質 `--only-l6` と `--with-l6` は同義。両立しても二重追加しない)。
      - only フラグが一切無ければ従来どおり tasks.jsonl を基点に上乗せ。
    """
    only_l6 = getattr(args, "only_l6", False)
    only_l7 = getattr(args, "only_l7", False)
    with_l6 = getattr(args, "with_l6", False)
    with_l7 = getattr(args, "with_l7", False)

    only_mode = only_l6 or only_l7
    ledgers = [] if only_mode else ["tasks.jsonl"]
    if only_l6 or with_l6:
        ledgers.append(args.l6_ledger)
    if only_l7 or with_l7:
        ledgers.append(args.l7_ledger)
    return ledgers


def cmd_list_tasks(args) -> int:
    tasks = load_tasks(Path(args.tasks_dir), ledgers=_ledgers(args))
    for t in tasks:
        print(f"{t.task_id}  [{t.difficulty:6s}]  {t.title}  ({len(t.files)} files)")
    print(f"total: {len(tasks)}")
    return 0


def cmd_models(args) -> int:
    """利用可能なモデルを一覧する (config定義 + Ollama稼働モデル)."""
    config = _load_config(args.config)
    models = config.get("models", {})
    print("=== config.yaml 定義モデル ===")
    if models:
        for k, v in models.items():
            extra = f", model={v['model']}" if v.get("model") else ""
            print(f"  {k:14s} (type={v.get('type', '?')}{extra})")
    else:
        print("  (なし)")

    if args.ollama_host:
        config.setdefault("run", {})["ollama_host"] = args.ollama_host
    host = BenchmarkRunner(config, Path(args.tasks_dir)).ollama_host()
    print(f"\n=== Ollama 稼働モデル ({host}) ===")
    try:
        names = list_ollama_models(host)
    except Exception as e:
        print(f"  ⚠️ Ollamaに接続できません: {e}")
        print("  (Ollamaを起動すると、ここのモデルを --model で直接指定できます)")
        return 0
    if names:
        for n in names:
            print(f"  {n}")
        print("  → config未定義でも `--model <名前>` でそのまま実行できます")
    else:
        print("  (インストール済みモデルなし。`ollama pull <model>` で追加)")
    return 0


def cmd_run(args) -> int:
    config = _load_config(args.config)
    if args.lang:
        config.setdefault("run", {})["issue_lang"] = args.lang
    if getattr(args, "ollama_host", None):
        config.setdefault("run", {})["ollama_host"] = args.ollama_host
    runner = BenchmarkRunner(config, Path(args.tasks_dir), ledgers=_ledgers(args))
    only = args.tasks.split(",") if args.tasks else None
    try:
        run = runner.run(
            args.model, only_tasks=only,
            runs=args.runs, sample_temp=args.sample_temp,
            label=args.label, concurrency=args.concurrency,
            client_type=args.client_type, base_url=args.base_url,
        )
    except ValueError as e:  # モデル解決失敗などは見やすく表示
        print(f"❌ {e}", file=sys.stderr)
        return 2
    json_path, md_path = save_run(run, Path(args.output))
    print()
    print(f"Resolved率   : {run.resolved_rate * 100:.1f}%")
    if run.multi_run:
        print(f"平均成功率   : {run.avg_success_rate * 100:.1f}% (pass@1 ×{run.runs})")
        print(f"≥1成功タスク : {run.solved_any_rate * 100:.1f}%")
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


def cmd_certify(args) -> int:
    """results.json を tier合格制で判定し「使えるライン」到達レベルを表示する."""
    import json

    from .certify import certify, merge_results, render_certificate_md

    if getattr(args, "merge", False):
        model, results = merge_results(args.results)
        cert = certify(results)
        print(render_certificate_md(cert, model or "merged"))
        print()
        return 0

    for path in args.results:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cert = certify(data.get("results", []))
        print(render_certificate_md(cert, data.get("model", "")))
        print()
    return 0


def cmd_validate(args) -> int:
    """gold/brokenモックで全パイプラインを自己検証する."""
    config = _load_config(args.config)
    config.setdefault("models", {})
    config["models"]["mock-gold"] = {"type": "mock", "mode": "gold"}
    config["models"]["mock-broken"] = {"type": "mock", "mode": "broken"}
    runner = BenchmarkRunner(config, Path(args.tasks_dir), ledgers=_ledgers(args))
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

    p_models = sub.add_parser("models", help="モデル一覧 (config + Ollama稼働)")
    _common_args(p_models)
    p_models.add_argument("--ollama-host", default=None, dest="ollama_host",
                          help="Ollama接続先 (既定: configまたはhttp://localhost:11434)")
    p_models.set_defaults(fn=cmd_models)

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
    p_run.add_argument("--ollama-host", default=None, dest="ollama_host",
                       help="Ollama接続先 (config未定義モデルの自動解決に使用)")
    p_run.add_argument(
        "--base-url", default=None, dest="base_url",
        help="接続先URLを明示指定 (configのbase_urlを上書き。"
             "例: http://localhost:8085/v1)",
    )
    p_run.add_argument(
        "--client-type", default=None, dest="client_type",
        choices=["openai", "ollama", "multiagent"],
        help="config未定義でも接続種別を直接指定 "
             "(openai=llama.cpp/vLLM等, ollama, multiagent=CodeRouter)。"
             "--base-url と併用",
    )
    p_run.add_argument("--label", default=None,
                       help="結果ラベルを明示指定 (既定: model:auto時はサーバ検出名)")
    p_run.add_argument(
        "--concurrency", type=int, default=None,
        help="試行(runs)を同時実行する並列数 (既定: run.concurrency または1)。"
             "llama.cpp を --parallel N -cb で起動した場合に有効",
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

    p_cert = sub.add_parser("certify", help="使えるライン判定 (tier合格制)")
    p_cert.add_argument("results", nargs="+", help="判定する results.json")
    p_cert.add_argument(
        "--merge", action="store_true",
        help="複数 results.json の results を合算して1つの認証を出す "
             "(分割実行した base40 + L6 等の統合認証。task_id重複は後勝ち)",
    )
    p_cert.set_defaults(fn=cmd_certify)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
