"""ベンチマーク実行オーケストレータ.

単一試行 (runs=1) では従来通り。runs>1 のときは各タスクをN回サンプリングし、
成功率・pass@k などの信頼性指標を集計する (「実際どれくらい使えるか」の核)。
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import env as envinfo
from . import usability
from .clients import LLMClient, create_client, sampling_of
from .clients.mock import MockClient
from .clients.ollama import (
    DEFAULT_OLLAMA_HOST,  # noqa: F401  (後方互換のため残置)
    default_ollama_host,
    list_ollama_models,
)
from .graders import GradeCtx, get_grader
from .scoring import combined_score, pass_at_k
from .tasks import Task, load_tasks


# results.json には載せない大きめのフィールド (artifactsとして別途ファイル保存する)
ARTIFACT_FIELDS = ("raw_output", "parsed_files", "test_output")


@dataclass
class Attempt:
    """1回の試行の評価結果."""

    resolved: bool = False
    quality_score: float = 0.0
    combined: float = 0.0
    fail_reason: str = ""
    latency_sec: float = 0.0
    tokens_per_sec: float | None = None
    completion_tokens: int | None = None
    parse_ok: bool = False
    parse_error: str = ""
    parsed_files: dict = field(default_factory=dict)
    raw_output: str = ""
    test_output: str = ""
    quality_components: dict = field(default_factory=dict)
    # 打ち切り (max_tokens 到達 / finish_reason=length)。
    # 「解けなかった」のか「言い終わる前に切られた」のかは別問題なので分けて残す。
    truncated: bool = False
    finish_reason: str = ""
    max_tokens: int | None = None


@dataclass
class TaskResult:
    task_id: str
    difficulty: str
    title: str = ""
    domain: str = "code"
    resolved: bool = False
    quality_score: float = 0.0
    combined: float = 0.0
    latency_sec: float = 0.0
    tokens_per_sec: float | None = None
    completion_tokens: int | None = None
    fail_reason: str = ""
    quality_components: dict = field(default_factory=dict)

    # --- 信頼性 (pass@k) ---
    runs: int = 1
    n_pass: int = 0
    success_rate: float = 0.0          # n_pass / runs
    pass_at_1: float = 0.0
    pass_at_k: float = 0.0
    pass_k: int = 1                    # pass_at_k の実際の k (既定は runs と同値)
    attempts: list = field(default_factory=list)   # 各試行の要約 (軽量)

    # --- 打ち切り ---
    truncated: bool = False          # いずれかの試行が max_tokens で切られた
    n_truncated: int = 0             # 打ち切られた試行数
    finish_reason: str = ""          # 代表試行の終了理由
    max_tokens: int | None = None    # 生成に使った max_tokens

    # --- usability判定 ---
    usability_tier: str = ""

    # --- 生成物 (artifacts / 代表試行) ---
    parse_ok: bool = False
    parse_error: str = ""
    parsed_files: dict = field(default_factory=dict)   # 相対パス -> 生成コード
    raw_output: str = ""                                # LLMの生出力
    test_output: str = ""                               # pytestの出力

    @property
    def changed_files(self) -> list[str]:
        return list(self.parsed_files.keys())


@dataclass
class RunResult:
    model: str
    issue_lang: str
    results: list[TaskResult] = field(default_factory=list)
    runs: int = 1
    artifacts_dirname: str = ""   # save_run時に生成物ディレクトリ名が入る
    served_model: str = ""        # 実際に応答したモデル名 (model:auto / type:cli の検出結果)
    # 実行環境 (ホストのCPU/GPU/RAM + 推論バックエンド構成)。env.collect() の戻り値。
    # tok/s は量子化・GPUオフロード率・n_ctx で数倍変わるので結果と同じJSONに残す。
    environment: dict = field(default_factory=dict)

    @property
    def multi_run(self) -> bool:
        return self.runs > 1 or any(r.runs > 1 for r in self.results)

    @property
    def resolved_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.resolved for r in self.results) / len(self.results)

    @property
    def avg_success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.success_rate for r in self.results) / len(self.results)

    @property
    def avg_pass_at_k(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.pass_at_k for r in self.results) / len(self.results)

    @property
    def solved_any_rate(self) -> float:
        """N回中1回でも成功したタスクの割合 (再試行込みで到達可能か)."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.n_pass > 0) / len(self.results)

    @property
    def avg_quality_resolved(self) -> float:
        """resolvedになったタスクのみの品質平均."""
        rs = [r.quality_score for r in self.results if r.resolved]
        return sum(rs) / len(rs) if rs else 0.0

    @property
    def avg_combined(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.combined for r in self.results) / len(self.results)


class BenchmarkRunner:
    def __init__(self, config: dict, tasks_root: Path, ledgers: list[str] | None = None):
        self.config = config
        self.tasks_root = tasks_root
        self.run_cfg = config.get("run", {})
        self.ledgers = ledgers or ["tasks.jsonl"]
        self.quality_cfg = config.get("quality", {})
        self.scoring_cfg = config.get("scoring", {})
        self.usability_cfg = config.get("usability", {})
        # pass@k の k (run.pass_k)。null/未設定なら runs と同値 = 従来挙動。
        self.pass_k = self.run_cfg.get("pass_k")
        wd = self.run_cfg.get("workdir")
        self.work_root = (
            Path(wd) if wd else Path(tempfile.gettempdir()) / "llmbench_work"
        )

    def ollama_host(self) -> str:
        """Ollama接続先の優先順:
        --ollama-host / run.ollama_host > env OLLAMA_HOST
        > configのollamaモデル base_url > http://localhost:11434
        """
        h = self.run_cfg.get("ollama_host")
        if h:
            return h
        env = os.environ.get("OLLAMA_HOST")
        if env:
            return env
        for v in self.config.get("models", {}).values():
            if v.get("type") == "ollama" and v.get("base_url"):
                return v["base_url"]
        return default_ollama_host()

    def _ollama_template(self) -> dict:
        """configにある最初のollamaモデルから共通パラメータを借用する."""
        for v in self.config.get("models", {}).values():
            if v.get("type") == "ollama":
                return {
                    k: v[k] for k in ("temperature", "max_tokens", "timeout")
                    if k in v
                }
        return {}

    def resolve_model(
        self,
        name: str,
        client_type: str | None = None,
        base_url: str | None = None,
    ) -> dict:
        """モデル名を接続設定(dict)に解決する.

        優先順:
          1. client_type 指定あり → config を経由せず ad-hoc に合成
             (--client-type openai --base-url http://... で llama.cpp 直結、
              --client-type multiagent で CodeRouter 直結など)
          2. config の models: キーに一致 → その設定
             (base_url 指定があれば上書き)
          3. Ollama 稼働モデル名 → ollama 設定を自動合成
             (base_url 指定があればそれを Ollama ホストとして使用)
        """
        models = self.config.get("models", {})
        if client_type:
            cfg = dict(models.get(name, {}))
            cfg["type"] = client_type
            if base_url:
                cfg["base_url"] = base_url
            if client_type == "ollama":
                cfg.setdefault("base_url", base_url or self.ollama_host())
                cfg = {**self._ollama_template(), **cfg}
            if name not in models:
                # openai型で名前がconfig未定義なら auto 扱い
                # (auto/実モデル名どちらでも可)
                cfg.setdefault("model", name)
            return cfg
        if name in models:
            cfg = dict(models[name])
            if base_url:
                cfg["base_url"] = base_url
            return cfg
        host = base_url or self.ollama_host()
        try:
            available = list_ollama_models(host)
        except Exception as e:  # Ollama未起動など
            raise ValueError(
                f"モデル {name!r} はconfig未定義で、"
                f"Ollama ({host}) にも接続できません: {e}\n"
                f"  config定義: {list(models)}\n"
                f"  (Ollama以外に繋ぐ場合は --client-type openai|multiagent "
                f"と --base-url を指定)"
            ) from e
        if name in available:
            return {**self._ollama_template(), "type": "ollama",
                    "base_url": host, "model": name}
        raise ValueError(
            f"モデル {name!r} はconfig未定義で、"
            f"Ollama ({host}) にも未インストールです。\n"
            f"  config定義: {list(models)}\n  Ollama稼働: {available}"
        )

    def _make_reviewer(self) -> LLMClient | None:
        cfg = self.quality_cfg.get("llm_review", {})
        if not cfg.get("enabled", False):
            return None
        name = cfg.get("reviewer_model")
        if not name:
            raise ValueError(
                "quality.llm_review.enabled ですが reviewer_model が未指定です"
            )
        try:
            # メインモデルと同じ解決経路 (config > Ollama自動解決)
            return create_client(name, self.resolve_model(name))
        except ValueError as e:
            raise ValueError(
                f"reviewer_model {name!r} を解決できません: {e}"
            ) from e

    def _make_judge(self) -> tuple[LLMClient | None, int]:
        """judge grader 用の採点モデルを構築する (quality.judge).

        未設定・無効なら (None, 1)。この場合 judge grader は hard_constraints のみで
        決定的に判定する (validate を緑に保つ)。
        """
        cfg = self.quality_cfg.get("judge", {})
        seeds = max(1, int(cfg.get("seeds", 1)))
        if not cfg.get("enabled", False):
            return None, seeds
        name = cfg.get("judge_model")
        if not name:
            raise ValueError("quality.judge.enabled ですが judge_model が未指定です")
        try:
            return create_client(name, self.resolve_model(name)), seeds
        except ValueError as e:
            raise ValueError(f"judge_model {name!r} を解決できません: {e}") from e

    def run(
        self,
        model_name: str,
        only_tasks: list[str] | None = None,
        progress=print,
        runs: int | None = None,
        sample_temp: float | None = None,
        label: str | None = None,
        concurrency: int | None = None,
        client_type: str | None = None,
        base_url: str | None = None,
        generate_retries: int | None = None,
    ) -> RunResult:
        model_cfg = self.resolve_model(
            model_name, client_type=client_type, base_url=base_url
        )
        # run.sampling があれば全モデル共通の既定として渡す (無ければ従来動作)
        client = create_client(
            model_name, model_cfg, defaults=self.run_cfg.get("sampling")
        )
        reviewer = self._make_reviewer()
        judge, judge_seeds = self._make_judge()
        lang = self.run_cfg.get("issue_lang", "en")
        timeout = int(self.run_cfg.get("test_timeout", 120))
        # パース失敗時の再生成回数。runs>1 では試行そのものが冗長性を持つので、
        # 生成が高価なモデル(思考モデル)では 0 にして時間を節約できる。
        retries = int(
            generate_retries if generate_retries is not None
            else self.run_cfg.get("generate_retries", 1)
        )
        retries = max(0, retries)
        runs = int(runs if runs is not None else self.run_cfg.get("runs", 1))
        runs = max(1, runs)
        self._concurrency = max(1, int(
            concurrency if concurrency is not None
            else self.run_cfg.get("concurrency", 1)
        ))
        # 複数試行時は多様性のためサンプリング温度を上げる
        if runs > 1:
            st = sample_temp if sample_temp is not None else self.run_cfg.get(
                "sample_temp", 0.8
            )
            client.temperature = float(st)

        # ラベル: --label > サーバ自動検出(model:auto) > config キー名
        served = getattr(client, "served_model_name", None)
        if label:
            run_label = label
        elif served:
            run_label = _label_from_model(served)
            progress(f"検出モデル: {served} (config未編集で自動採用)")
        else:
            run_label = model_name

        tasks = load_tasks(self.tasks_root, only=only_tasks, ledgers=self.ledgers)
        run = RunResult(model=run_label, issue_lang=lang, runs=runs)

        for i, task in enumerate(tasks, 1):
            progress(
                f"[{i}/{len(tasks)}] {task.task_id} ({task.difficulty}) {task.title}"
                + (f"  ×{runs}" if runs > 1 else "")
            )
            # 性能制約タスクは個別 perf_timeout を優先 (無ければ config 既定)
            task_timeout = task.perf_timeout or timeout
            tr = self._run_task(
                client, reviewer, judge, judge_seeds,
                task, lang, task_timeout, retries, runs,
            )
            run.results.append(tr)
            _log_task(progress, tr)

        # 実際に応答したモデル名を記録:
        #   model:auto → served_model_name / type:cli → 生成中にCLI応答から検出
        detected = getattr(client, "detected_model", None)
        run.served_model = served or detected or ""
        if detected:
            progress(f"実行モデル : {detected} (CLI応答から検出 → resultsに記録)")

        # 実行環境を記録 (ハード + バックエンド構成)。
        # 生成を1回以上通した後に取るのは、Ollama の /api/ps が
        # 「ロード済みモデル」しか返さない = 実行前だと空になるため。
        # 収集は best-effort で、失敗してもベンチ結果には影響させない。
        run.environment = envinfo.collect(
            model_cfg, served_model=run.served_model or None
        )
        # サンプリング設定は「同じ条件で測ったか」の核。runs>1 では上で
        # client.temperature を実行時に上書きしているので、**上書き後の実効値**
        # を記録する (config の値ではない)。
        run.environment["sampling"] = sampling_of(client)
        summary = envinfo.format_summary(run.environment)
        if summary:
            progress(f"実行環境   : {summary}")
        return run

    def _one_attempt(
        self,
        client: LLMClient,
        grader,
        system: str,
        user_prompt: str,
        task: Task,
        ctx: GradeCtx,
        retries: int,
    ) -> Attempt:
        """1回分の 生成→採点 を評価する (grader 差し替え可)."""
        at = Attempt()
        total_latency = 0.0
        gen = None
        ev = None
        # 再生成ゲート: parse_ok だけでは足りない。「一部のパスがプレースホルダ
        # だったので捨てた」ようなケースは parse_ok=True でも中身が疑わしいので、
        # grader が警告を返したときも作り直す。ループは必ず retries+1 回で抜ける。
        for _ in range(retries + 1):
            t_gen = time.monotonic()
            try:
                gen = client.generate(system, user_prompt)
            except Exception as e:  # 生成失敗はその試行を失敗扱い
                # 失敗時も経過時間を残す。ここを 0.0 のままにしていたため
                # 600秒待った Read timeout がログ上 "(0.0s)" と表示され、
                # 「即死」に見えて原因の切り分けを妨げていた。
                at.latency_sec = round(
                    total_latency + (time.monotonic() - t_gen), 2
                )
                at.fail_reason = f"generation error: {e}"
                return at
            total_latency += gen.latency_sec
            ev = grader.evaluate(task, gen.text, ctx)
            if ev.parse_ok and not _extraction_suspect(ev):
                break
        at.latency_sec = round(total_latency, 2)
        if gen is not None:
            at.tokens_per_sec = (
                round(gen.tokens_per_sec, 1) if gen.tokens_per_sec else None
            )
            at.completion_tokens = gen.completion_tokens
            at.raw_output = gen.text
            # 古いクライアント実装 (追加フィールドを持たない) でも壊れないよう getattr
            at.truncated = bool(getattr(gen, "truncated", False))
            at.finish_reason = getattr(gen, "finish_reason", None) or ""
            at.max_tokens = getattr(gen, "max_tokens", None)
        if ev is not None:
            at.resolved = ev.resolved
            at.quality_score = ev.quality_score
            at.parse_ok = ev.parse_ok
            at.parse_error = ev.parse_error
            at.parsed_files = ev.parsed_files
            at.fail_reason = ev.fail_reason or at.fail_reason
            at.test_output = ev.detail_output
            at.quality_components = ev.components

        at.combined = combined_score(at.resolved, at.quality_score, self.scoring_cfg)
        return at

    def _run_task(
        self,
        client: LLMClient,
        reviewer: LLMClient | None,
        judge: LLMClient | None,
        judge_seeds: int,
        task: Task,
        lang: str,
        timeout: int,
        retries: int,
        runs: int = 1,
    ) -> TaskResult:
        tr = TaskResult(
            task_id=task.task_id, difficulty=task.difficulty, title=task.title,
            domain=task.domain, runs=runs,
        )
        if isinstance(client, MockClient):
            client.current_task = task
            client.current_task_dir = task.dir   # 後方互換

        grader = get_grader(task.grader)
        system, user_prompt = grader.build_prompt(task, lang)
        ctx = GradeCtx(
            work_root=self.work_root,
            quality_cfg=self.quality_cfg,
            scoring_cfg=self.scoring_cfg,
            graders_cfg=self.config.get("graders", {}),
            reviewer=reviewer, judge=judge, judge_seeds=judge_seeds,
            timeout=timeout, lang=lang,
        )

        def _attempt(_i):
            return self._one_attempt(
                client, grader, system, user_prompt, task, ctx, retries
            )

        # 試行(runs)を並列実行する。LLM生成がボトルネックなので、サーバ側を
        # `--parallel N -cb` で起動しておけば runs 本の生成が重なって時間短縮できる。
        # MockClient は task_dir 状態を共有するため直列にフォールバックする。
        conc = min(getattr(self, "_concurrency", 1), runs)
        if conc > 1 and not isinstance(client, MockClient):
            with ThreadPoolExecutor(max_workers=conc) as ex:
                attempts = list(ex.map(_attempt, range(runs)))
        else:
            attempts = [_attempt(i) for i in range(runs)]
        _aggregate_attempts(tr, attempts, self.scoring_cfg, k=self.pass_k)
        tr.usability_tier = usability.classify(
            tr.success_rate, tr.quality_score, self.usability_cfg
        )
        return tr


def _extraction_suspect(ev) -> bool:
    """抽出はできたが鵜呑みにできない (= 再生成する価値がある) か.

    ``GraderEval.parse_warnings`` は patch 側の warnings (プレースホルダの
    パスを捨てた等)。持たない grader でも壊れないよう getattr で読む。
    """
    return bool(
        getattr(ev, "parse_warnings", None) or getattr(ev, "parse_error", "")
    )


def _aggregate_attempts(
    tr: TaskResult, attempts: list[Attempt], scoring_cfg: dict, k: int | None = None
) -> None:
    """複数試行を集計し TaskResult を埋める. runs=1 なら従来値と一致する.

    k は pass@k の k。None (既定) なら k = n となり、従来どおり
    「1回でも成功したか」の 0/1 に退化する。k < n を指定すると
    「k回試して1回でも成功する確率」の不偏推定として意味を持つ。
    """
    n = len(attempts)
    passed = [a for a in attempts if a.resolved]
    c = len(passed)

    k_eff = n if k is None else max(1, min(int(k), n))
    tr.n_pass = c
    tr.success_rate = round(c / n, 3) if n else 0.0
    tr.pass_at_1 = tr.success_rate
    tr.pass_k = k_eff
    tr.pass_at_k = round(pass_at_k(n, c, k_eff), 3)

    # 品質: 成功試行の平均 (1つも成功しなければ0)
    tr.quality_score = round(sum(a.quality_score for a in passed) / c, 1) if c else 0.0
    # 複合: 成功率でスケール (runs=1 なら resolved 0/1 と等価)
    tr.combined = combined_score(tr.success_rate, tr.quality_score, scoring_cfg)
    # headline resolved は多数決 (runs=1 なら単一試行と一致)
    tr.resolved = tr.success_rate >= 0.5

    # 速度メトリクスは平均
    tr.latency_sec = round(sum(a.latency_sec for a in attempts) / n, 2) if n else 0.0
    tps = [a.tokens_per_sec for a in attempts if a.tokens_per_sec]
    tr.tokens_per_sec = round(sum(tps) / len(tps), 1) if tps else None
    toks = [a.completion_tokens for a in attempts if a.completion_tokens]
    tr.completion_tokens = round(sum(toks) / len(toks)) if toks else None

    # 打ち切り: 1試行でも切られていれば「このタスクは上限に当たっている」
    tr.n_truncated = sum(1 for a in attempts if a.truncated)
    tr.truncated = tr.n_truncated > 0
    mt = [a.max_tokens for a in attempts if a.max_tokens]
    tr.max_tokens = mt[0] if mt else None

    # 失敗理由
    if c == n:
        tr.fail_reason = ""
    elif c == 0:
        tr.fail_reason = attempts[0].fail_reason if attempts else ""
    else:
        tr.fail_reason = f"flaky {c}/{n} passed"

    # 代表試行 (artifacts用): 最初の成功試行、なければ最初の試行
    rep = passed[0] if passed else (attempts[0] if attempts else Attempt())
    tr.parse_ok = rep.parse_ok
    tr.parse_error = rep.parse_error
    tr.parsed_files = rep.parsed_files
    tr.raw_output = rep.raw_output
    tr.test_output = rep.test_output
    tr.quality_components = rep.quality_components
    tr.finish_reason = rep.finish_reason

    # 試行ごとの軽量サマリ (JSONに残す)
    tr.attempts = [
        {
            "resolved": a.resolved,
            "quality": round(a.quality_score, 1),
            "combined": a.combined,
            "fail_reason": a.fail_reason,
            "truncated": a.truncated,
            "finish_reason": a.finish_reason,
        }
        for a in attempts
    ]


_UNSAFE_FILENAME_CHARS = '<>:"|?*'


def _safe_label(name: str) -> str:
    """モデル名/ラベルをファイル名に埋め込める形に正規化する.

    Ollama では `hf.co/unsloth/Qwen3-Coder-GGUF:Q4_K_M` のようにスラッシュと
    コロンを含むモデル名が標準的で、そのままファイル名にすると存在しない
    ディレクトリを指して FileNotFoundError になる (採点済み結果が消える)。
    表示用の原文は run.model 側に残し、ここでは**ファイル名専用**の slug を作る。
    """
    seg = str(name or "").replace("\\", "/").rsplit("/", 1)[-1]
    out = "".join(
        "-" if (ch in _UNSAFE_FILENAME_CHARS or ord(ch) < 32) else ch
        for ch in seg
    )
    out = out.strip(" .")
    return out or "model"


def _label_from_model(name: str) -> str:
    """サーバ報告のモデル名を結果ラベル用に整える (パス/.gguf除去)."""
    name = name.rsplit("/", 1)[-1]
    if name.endswith(".gguf"):
        name = name[:-5]
    return name


def _snippet(text: str, n: int = 3) -> str:
    """先頭n行を1行に潰したプレビュー."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    head = " ⏎ ".join(lines[:n])
    return head[:120] + ("…" if len(head) > 120 else "")


def _log_task(progress, tr: TaskResult) -> None:
    """生成物の中身が分かるようにタスク結果をログ出力する."""
    # 1行目: パース結果と生成ファイル
    if tr.parse_ok:
        files = ", ".join(tr.changed_files) or "(なし)"
        progress(
            f"    生成OK  files=[{files}]  "
            f"{tr.completion_tokens or '?'}tok @ {tr.tokens_per_sec or '?'}tok/s"
        )
    else:
        progress(f"    生成パース失敗: {tr.parse_error or '不明'}")
        if tr.raw_output:
            progress(f"      出力プレビュー: {_snippet(tr.raw_output)}")

    # 2行目: 各生成ファイルの行数とコード冒頭 (動いてるか目視確認用)
    for path, code in tr.parsed_files.items():
        nloc = len([ln for ln in code.splitlines() if ln.strip()])
        progress(f"      └ {path} ({nloc} LOC): {_snippet(code, 2)}")

    # 3行目: 判定 (複数試行なら信頼性も)
    status = "✅ RESOLVED" if tr.resolved else f"❌ FAILED ({tr.fail_reason})"
    tier = usability.TIER_LABEL.get(tr.usability_tier, "")
    if tr.runs > 1:
        progress(
            f"    {status}  成功 {tr.n_pass}/{tr.runs} "
            f"(pass@1={tr.pass_at_1:.2f} pass@{tr.runs}={tr.pass_at_k:.2f})  "
            f"quality={tr.quality_score:.0f} combined={tr.combined:.0f}  "
            f"[{tier}]  ({tr.latency_sec:.1f}s)"
        )
    else:
        progress(
            f"    {status}  quality={tr.quality_score:.0f} "
            f"combined={tr.combined:.0f}  [{tier}]  ({tr.latency_sec:.1f}s)"
        )
    # テスト失敗時はpytest出力の末尾を出す
    if not tr.resolved and tr.test_output:
        tail = tr.test_output.strip().splitlines()[-3:]
        for ln in tail:
            progress(f"      | {ln}")


def _write_artifacts(run: RunResult, artifacts_dir: Path) -> None:
    """タスクごとに生成物 (LLM生出力・生成コード・テスト出力) をファイル保存する."""
    for r in run.results:
        tdir = artifacts_dir / r.task_id
        tdir.mkdir(parents=True, exist_ok=True)

        # LLMの生出力
        if r.raw_output:
            (tdir / "llm_output.txt").write_text(r.raw_output, encoding="utf-8")

        # 生成された各ファイル (実際に適用されるコードそのもの)
        code_dir = tdir / "generated"
        for rel, content in r.parsed_files.items():
            dest = code_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not content.endswith("\n"):
                content += "\n"
            dest.write_text(content, encoding="utf-8")

        # pytest出力 (失敗原因の確認用)
        if r.test_output:
            (tdir / "test_output.txt").write_text(r.test_output, encoding="utf-8")


def save_run(run: RunResult, output_dir: Path) -> tuple[Path, Path]:
    """結果をJSON・Markdown・生成物として保存. (json_path, md_path) を返す."""
    from .report import render_markdown

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    # ファイル名にはサニタイズ済み slug を使う (run.model 自体は原文のまま)。
    slug = _safe_label(run.model)
    json_path = output_dir / f"{stamp}_{slug}_results.json"
    md_path = output_dir / f"{stamp}_{slug}_report.md"
    artifacts_dir = output_dir / f"{stamp}_{slug}_artifacts"

    # 生成物を別ディレクトリに保存
    _write_artifacts(run, artifacts_dir)
    run.artifacts_dirname = artifacts_dir.name

    # results.json は集計・スコア中心に保つ (大きいartifactフィールドは除外)
    def _lean(r: TaskResult) -> dict:
        d = asdict(r)
        for k in ARTIFACT_FIELDS:
            d.pop(k, None)
        return d

    # 各 TaskResult に usability_tier は設定済みなので cfg は不要
    overall, by_diff = usability.aggregate(run.results)
    summary = {
        "resolved_rate": round(run.resolved_rate, 3),
        "avg_quality_resolved": round(run.avg_quality_resolved, 1),
        "avg_combined": round(run.avg_combined, 1),
        "n_tasks": len(run.results),
        "runs": run.runs,
        # max_tokens で打ち切られたタスク数。0 でないランは「解けなかった」の
        # 内訳に「言い終わる前に切られた」が混ざっているので、スコアだけを見て
        # モデルの実力と読んではいけない。
        "n_truncated": sum(1 for r in run.results if r.truncated),
        "usability": {t: overall.get(t, 0) for t in usability.TIERS},
    }
    # 速度指標も summary に置く。従来はタスク単位 (results[]) にしか無く、
    # summary だけを読む外部ツール (CodeRouter のスイープ結果パネル等) から
    # 速度が見えなかった。キー名は汎用の tokens_per_sec / avg_latency_ms。
    tps = [r.tokens_per_sec for r in run.results if r.tokens_per_sec]
    if tps:
        summary["tokens_per_sec"] = round(sum(tps) / len(tps), 1)
    lat = [r.latency_sec for r in run.results if r.latency_sec]
    if lat:
        summary["avg_latency_ms"] = round(sum(lat) / len(lat) * 1000)
    if run.multi_run:
        # avg_success_rate=平均pass@1, solved_any_rate=N回中≥1成功
        # avg_pass_at_k は run.pass_k で指定した k での不偏推定
        # (k == runs のときは solved_any_rate と同義に退化する)
        summary["avg_success_rate"] = round(run.avg_success_rate, 3)
        summary["solved_any_rate"] = round(run.solved_any_rate, 3)
        summary["avg_pass_at_k"] = round(run.avg_pass_at_k, 3)

    payload = {
        "model": run.model,
        "issue_lang": run.issue_lang,
        "artifacts_dir": artifacts_dir.name,
        "summary": summary,
        "results": [_lean(r) for r in run.results],
    }
    if run.served_model:
        payload["served_model"] = run.served_model
    if run.environment:
        payload["environment"] = run.environment
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(render_markdown(run), encoding="utf-8")
    return json_path, md_path
