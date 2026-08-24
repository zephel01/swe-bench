"""llmbench CLI.

使用例:
    llmbench list-tasks
    llmbench models                                  # config定義 + Ollama稼働モデル
    llmbench models --remote opencode-go             # type:openai の /v1/models を照会
                                                       # (OpenCode Go 等が実際に提供するモデルID一覧)
    llmbench run --model local-ollama
    llmbench run --model local-openai --tasks t001,t003 --lang ja
    llmbench preflight --model local-openai          # 走らせる前に設定を照合
    llmbench validate                                # gold/brokenモックで自己検証
    llmbench certify results/<stamp>_<model>_results.json      # 使えるライン判定
    llmbench certify --merge results/base.json results/l7.json # 分割実行を統合判定
    llmbench compare results/a_results.json results/b_results.json  # 横断比較
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .clients.base import expand_env
from .clients.ollama import list_ollama_models
from .clients.openai_compat import list_remote_models
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
        help="既定40問に加えて L7 (grandmaster tier) の追加16問を含める "
             "(L6 は含まない。併用は --with-l6 も指定)",
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
        help="既定40問を除外し L7 (grandmaster) の追加台帳(16問)だけを実行する",
    )
    # --- ドメイン台帳 (コーディング以外) ---
    for dom, desc in (
        ("sec", "security 検出/解析"),
        ("secaug", "security 摂動変種 (SecLLMHolmes式 augmentation)"),
        ("gen", "general 一般タスク/指示追従"),
        ("write", "writing 創作 (experimental)"),
        ("med", "medical QA (参考値)"),
        ("culture", "culture 日本のネットミーム知識 (参考値)"),
        ("unc", "uncensored 過剰拒否 (over-refusal) 検査 (参考値)"),
    ):
        parser.add_argument(
            f"--with-{dom}", action="store_true", dest=f"with_{dom}",
            help=f"既定タスクに {desc} 台帳 (tasks_{dom}.jsonl) を上乗せする",
        )
        parser.add_argument(
            f"--only-{dom}", action="store_true", dest=f"only_{dom}",
            help=f"既定タスク(tasks.jsonl)を除外して {desc} 台帳を実行する "
                 f"(他の --with-* / --only-* を併用すればそれらも加わる)",
        )


# ドメイン名 -> 台帳ファイル名
_DOMAIN_LEDGERS = {
    "sec": "tasks_sec.jsonl",
    "secaug": "tasks_sec_aug.jsonl",
    "gen": "tasks_gen.jsonl",
    "write": "tasks_write.jsonl",
    "med": "tasks_med.jsonl",
    "culture": "tasks_culture.jsonl",
    "unc": "tasks_unc.jsonl",
}


def _ledgers(args) -> list[str]:
    """実行対象の台帳リストを決める.

    優先規則:
      - `--only-l6` / `--only-l7` / `--only-{sec,gen,write,med,culture}` のいずれかが
        指定されたら「only モード」(tier 台帳だけでなくドメイン台帳の
        `--only-*` でも起動する)。
        既定台帳 tasks.jsonl を除外し、要求された台帳だけを対象にする。
        `--only-*` を複数指定すればその全てが対象になる。
      - only モードでも `--with-l6`/`--with-l7` は同 tier の追加要求として尊重する
        (実質 `--only-l6` と `--with-l6` は同義。両立しても二重追加しない)。
      - only フラグが一切無ければ従来どおり tasks.jsonl を基点に上乗せ。
    """
    only_l6 = getattr(args, "only_l6", False)
    only_l7 = getattr(args, "only_l7", False)
    with_l6 = getattr(args, "with_l6", False)
    with_l7 = getattr(args, "with_l7", False)

    only_dom = {d for d in _DOMAIN_LEDGERS if getattr(args, f"only_{d}", False)}
    with_dom = {d for d in _DOMAIN_LEDGERS if getattr(args, f"with_{d}", False)}

    only_mode = only_l6 or only_l7 or bool(only_dom)
    ledgers = [] if only_mode else ["tasks.jsonl"]
    if only_l6 or with_l6:
        ledgers.append(args.l6_ledger)
    if only_l7 or with_l7:
        ledgers.append(args.l7_ledger)
    for d in _DOMAIN_LEDGERS:
        if d in only_dom or d in with_dom:
            ledgers.append(_DOMAIN_LEDGERS[d])
    return ledgers


def cmd_list_tasks(args) -> int:
    tasks = load_tasks(Path(args.tasks_dir), ledgers=_ledgers(args))
    for t in tasks:
        cat = f"  {{{t.category}}}" if getattr(t, "category", "") else ""
        print(f"{t.task_id}  [{t.difficulty:6s}]  {t.title}{cat}  ({len(t.files)} files)")
    print(f"total: {len(tasks)}")
    return 0


def cmd_models(args) -> int:
    """利用可能なモデルを一覧する.

    既定: config定義 + Ollama稼働モデル。
    --remote <名前> を付けると、config.yaml の models.<名前> (type: openai)
    が実際に接続先で提供しているモデルIDを /v1/models から取得して表示する
    (例: OpenCode Go のようにモデルを都度差し替えられるゲートウェイの調査用)。
    """
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
    else:
        if names:
            for n in names:
                print(f"  {n}")
            print("  → config未定義でも `--model <名前>` でそのまま実行できます")
        else:
            print("  (インストール済みモデルなし。`ollama pull <model>` で追加)")

    if getattr(args, "remote", None):
        _print_remote_models(args.remote, models)
    return 0


def _print_remote_models(name: str, models: dict) -> None:
    """`llmbench models --remote <name>` の中身. /v1/models を照会して表示する."""
    entry = models.get(name)
    print(f"\n=== {name} が提供するモデル (/v1/models) ===")
    if entry is None:
        print(f"  ⚠️ config.yaml に models.{name} がありません")
        return
    if entry.get("type") != "openai":
        print(
            f"  ⚠️ models.{name} は type={entry.get('type')!r} です。"
            " --remote は type: openai (OpenAI互換 /v1/models を持つエンドポイント)"
            " のみ対応しています"
        )
        return
    try:
        base_url = expand_env(entry.get("base_url", ""), where=f"models.{name}.base_url")
        api_key = expand_env(entry.get("api_key", ""), where=f"models.{name}.api_key")
    except ValueError as e:
        print(f"  ⚠️ {e}")
        return
    if not base_url:
        print(f"  ⚠️ models.{name} に base_url がありません")
        return
    try:
        items = list_remote_models(base_url, api_key)
    except Exception as e:
        print(f"  ⚠️ {base_url}/models を取得できません: {e}")
        return
    if not items:
        print("  (0件。エンドポイントが空リストを返しました)")
        return
    for it in sorted(items, key=lambda x: (x.get("id") or x.get("model") or "")):
        model_id = it.get("id") or it.get("model") or "?"
        owner = it.get("owned_by")
        extra = f"  (owned_by={owner})" if owner else ""
        print(f"  {model_id}{extra}")
    current = entry.get("model")
    print(
        f"  → 現在の config.yaml: model: \"{current}\" "
        "(上の一覧のIDに書き換えて切替可能)"
    )


def _preflight_gate(args, config: dict) -> int | None:
    """ベンチを走らせる前に設定を照合する。FAIL なら走らせない.

    2026-08 に temperature 0.2 のまま16ラン(9.3時間)を回して測り直した。
    知識の問題ではなく「チェックを人手に任せていた」ことが原因なので、
    忘れても効くようにここで止める。

    - FAIL: 走らせない (--skip-preflight で無視できる)
    - WARN/INFO: 表示して続行
    - 生成は1トークンも行わないので、実行時間はほぼゼロ
    """
    if getattr(args, "skip_preflight", False):
        return None
    try:
        from .preflight import run_preflight
        report = run_preflight(config, args.model)
    except Exception as e:      # preflight 自体の失敗でベンチを止めない
        print(f"⚠️  preflight を実行できませんでした ({e})。続行します", file=sys.stderr)
        return None
    if report.worst in ("WARN", "FAIL"):
        print(report.render(), file=sys.stderr)
        print(file=sys.stderr)
    if report.worst == "FAIL":
        print("❌ preflight が FAIL です。設定を直してから再実行してください。",
              file=sys.stderr)
        print("   この判定を承知で走らせるなら --skip-preflight を付けてください。",
              file=sys.stderr)
        return 2
    return None


def cmd_run(args) -> int:
    config = _load_config(args.config)
    if args.lang:
        config.setdefault("run", {})["issue_lang"] = args.lang
    if getattr(args, "ollama_host", None):
        config.setdefault("run", {})["ollama_host"] = args.ollama_host
    gate = _preflight_gate(args, config)
    if gate is not None:
        return gate
    runner = BenchmarkRunner(config, Path(args.tasks_dir), ledgers=_ledgers(args))
    only = args.tasks.split(",") if args.tasks else None
    try:
        run = runner.run(
            args.model, only_tasks=only,
            runs=args.runs, sample_temp=args.sample_temp,
            label=args.label, concurrency=args.concurrency,
            client_type=args.client_type, base_url=args.base_url,
            generate_retries=args.generate_retries,
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


def _certify_gates(args) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    """config.yaml から certify 用のゲート設定を読む (失敗しても落とさない).

    certify は results.json さえあれば動くのが利点なので、config が無い/壊れて
    いる場合は既定ゲートにフォールバックする。
    """
    path = Path(getattr(args, "config", "config.yaml") or "config.yaml")
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"⚠️  config を読めないため既定ゲートを使います ({path}: {e})",
              file=sys.stderr)
        return None, None, None, None
    dom = cfg.get("certify_domains") or None
    med = cfg.get("certify_medical") or None
    cul = cfg.get("certify_culture") or None
    unc = cfg.get("certify_uncensored") or None
    return dom, med, cul, unc


def cmd_certify(args) -> int:
    """results.json を tier合格制で判定し「使えるライン」到達レベルを表示する."""
    import json

    from .certify import (
        certify, certify_culture, certify_domains, certify_medical,
        certify_uncensored, merge_results, render_certificate_md,
        render_culture_md, render_domains_md, render_medical_md,
        render_uncensored_md,
    )

    dom_gates, med_gates, cul_gates, unc_gates = _certify_gates(args)

    def _emit(results: list[dict], model: str) -> None:
        print(render_certificate_md(certify(results), model))
        dom = render_domains_md(certify_domains(results, dom_gates))
        if dom:
            print("\n" + dom)
        med = render_medical_md(certify_medical(results, med_gates))
        if med:
            print("\n" + med)
        cul = render_culture_md(certify_culture(results, cul_gates))
        if cul:
            print("\n" + cul)
        unc = render_uncensored_md(certify_uncensored(results, unc_gates))
        if unc:
            print("\n" + unc)
        print()

    if getattr(args, "merge", False):
        model, results = merge_results(args.results)
        _emit(results, model or "merged")
        return 0

    for path in args.results:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        _emit(data.get("results", []), data.get("model", ""))
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


def cmd_preflight(args) -> int:
    """走らせる前に「設定が本当に効いているか」を照合する.

    A. 公式推奨サンプリングとの差分
    B. config / 実payload / サーバ既定(/props) / 起動引数 の三点照合
    C. 既存 artifacts の縮退指数 (--scan)

    どれも生成を行わないので GPU 時間はかからない。
    """
    from .preflight import run_preflight

    config = {}
    if args.model:
        config = _load_config(args.config)
    report = run_preflight(
        config, args.model,
        artifacts=args.scan, results_json=args.results,
        offline=args.offline,
    )
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.render())
    return report.exit_code(strict=args.strict)


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
    p_models.add_argument(
        "--remote", default=None,
        help="config.yaml の models.<名前> (type: openai) が実際に提供する"
             "モデルIDを /v1/models から取得して表示する"
             " (例: --remote opencode-go でOpenCode Goの選択肢を調査)",
    )
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
        "--generate-retries", type=int, default=None, dest="generate_retries",
        help="パース失敗時の再生成回数 (既定: run.generate_retries または1)。"
             "runs>1 は試行自体が冗長なので、生成が高価なモデルでは 0 推奨",
    )
    p_run.add_argument(
        "--concurrency", type=int, default=None,
        help="試行(runs)を同時実行する並列数 (既定: run.concurrency または1)。"
             "llama.cpp を --parallel N -cb で起動した場合に有効",
    )
    p_run.add_argument(
        "--skip-preflight", action="store_true", dest="skip_preflight",
        help="実行前の設定照合 (preflight) を省略する。"
             "FAIL でも走らせたいときだけ使う",
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
        "--config", default="config.yaml",
        help="ゲート設定 (certify_domains / certify_medical / certify_culture / "
             "certify_uncensored) を読む config。"
             "読めない場合は既定ゲートにフォールバックする",
    )
    p_cert.add_argument(
        "--merge", action="store_true",
        help="複数 results.json の results を合算して1つの認証を出す "
             "(分割実行した base40 + L6 等の統合認証。task_id重複は後勝ち)",
    )
    p_cert.set_defaults(fn=cmd_certify)

    p_pre = sub.add_parser(
        "preflight",
        help="走らせる前の設定照合 (公式推奨との差分 / 実効値 / 縮退指数)",
    )
    p_pre.add_argument("--config", default="config.yaml")
    p_pre.add_argument("--model", default=None,
                       help="照合するモデル名 (省略時は --scan だけ実行)")
    p_pre.add_argument("--scan", default=None,
                       help="縮退指数を出す artifacts ディレクトリ")
    p_pre.add_argument("--results", default=None,
                       help="打ち切り率の集計に使う results.json "
                            "(省略時は --scan の隣から推測)")
    p_pre.add_argument("--offline", action="store_true",
                       help="HuggingFace を見に行かず、キャッシュと同梱テーブルだけを使う")
    p_pre.add_argument("--strict", action="store_true",
                       help="WARN でも exit 1 にする (CI 用)")
    p_pre.add_argument("--json", action="store_true", help="JSON で出力")
    p_pre.set_defaults(fn=cmd_preflight)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
