"""ベンチマーク実行オーケストレータ.

単一試行 (runs=1) では従来通り。runs>1 のときは各タスクをN回サンプリングし、
成功率・pass@k などの信頼性指標を集計する (「実際どれくらい使えるか」の核)。
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import sandbox, usability
from .clients import LLMClient, create_client
from .clients.mock import MockClient
from .functional import evaluate_functional
from .patch import parse_llm_output
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .quality import evaluate_quality
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


@dataclass
class TaskResult:
    task_id: str
    difficulty: str
    title: str = ""
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
    attempts: list = field(default_factory=list)   # 各試行の要約 (軽量)

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
    def __init__(self, config: dict, tasks_root: Path):
        self.config = config
        self.tasks_root = tasks_root
        self.run_cfg = config.get("run", {})
        self.quality_cfg = config.get("quality", {})
        self.scoring_cfg = config.get("scoring", {})
        self.usability_cfg = config.get("usability", {})
        wd = self.run_cfg.get("workdir")
        self.work_root = (
            Path(wd) if wd else Path(tempfile.gettempdir()) / "llmbench_work"
        )

    def _make_reviewer(self) -> LLMClient | None:
        cfg = self.quality_cfg.get("llm_review", {})
        if not cfg.get("enabled", False):
            return None
        name = cfg.get("reviewer_model")
        models = self.config.get("models", {})
        if name not in models:
            raise ValueError(f"reviewer_model {name!r} not in models config")
        return create_client(name, models[name])

    def run(
        self,
        model_name: str,
        only_tasks: list[str] | None = None,
        progress=print,
        runs: int | None = None,
        sample_temp: float | None = None,
    ) -> RunResult:
        models = self.config.get("models", {})
        if model_name not in models:
            raise ValueError(
                f"model {model_name!r} not found. available: {list(models)}"
            )
        client = create_client(model_name, models[model_name])
        reviewer = self._make_reviewer()
        lang = self.run_cfg.get("issue_lang", "en")
        timeout = int(self.run_cfg.get("test_timeout", 120))
        retries = int(self.run_cfg.get("generate_retries", 1))
        runs = int(runs if runs is not None else self.run_cfg.get("runs", 1))
        runs = max(1, runs)
        # 複数試行時は多様性のためサンプリング温度を上げる
        if runs > 1:
            st = sample_temp if sample_temp is not None else self.run_cfg.get(
                "sample_temp", 0.8
            )
            client.temperature = float(st)

        tasks = load_tasks(self.tasks_root, only=only_tasks)
        run = RunResult(model=model_name, issue_lang=lang, runs=runs)

        for i, task in enumerate(tasks, 1):
            progress(
                f"[{i}/{len(tasks)}] {task.task_id} ({task.difficulty}) {task.title}"
                + (f"  ×{runs}" if runs > 1 else "")
            )
            tr = self._run_task(client, reviewer, task, lang, timeout, retries, runs)
            run.results.append(tr)
            _log_task(progress, tr)
        return run

    def _one_attempt(
        self,
        client: LLMClient,
        reviewer: LLMClient | None,
        task: Task,
        issue: str,
        user_prompt: str,
        timeout: int,
        retries: int,
    ) -> Attempt:
        """1回分の 生成→パース→テスト→品質→スコア を評価する."""
        at = Attempt()
        patch = None
        total_latency = 0.0
        gen = None
        for _ in range(retries + 1):
            try:
                gen = client.generate(SYSTEM_PROMPT, user_prompt)
            except Exception as e:  # 生成失敗はその試行を失敗扱い
                at.fail_reason = f"generation error: {e}"
                return at
            total_latency += gen.latency_sec
            patch = parse_llm_output(gen.text, task.files)
            if patch.parse_ok:
                break
        at.latency_sec = round(total_latency, 2)
        if gen is not None:
            at.tokens_per_sec = (
                round(gen.tokens_per_sec, 1) if gen.tokens_per_sec else None
            )
            at.completion_tokens = gen.completion_tokens
            at.raw_output = gen.text
        if patch is not None:
            at.parse_ok = patch.parse_ok
            at.parse_error = patch.error
            at.parsed_files = dict(patch.files)

        func, ws = evaluate_functional(
            task.dir, patch, self.work_root, timeout=timeout, keep_workspace=True
        )
        at.resolved = func.resolved
        at.fail_reason = func.fail_reason
        at.test_output = func.test_output
        try:
            if ws is not None and func.applied_files:
                q = evaluate_quality(
                    ws, func.applied_files, self.quality_cfg,
                    issue_text=issue, reviewer_client=reviewer,
                )
                at.quality_score = q.score
                at.quality_components = q.components
        finally:
            if ws is not None:
                sandbox.cleanup(ws)

        at.combined = combined_score(at.resolved, at.quality_score, self.scoring_cfg)
        return at

    def _run_task(
        self,
        client: LLMClient,
        reviewer: LLMClient | None,
        task: Task,
        lang: str,
        timeout: int,
        retries: int,
        runs: int = 1,
    ) -> TaskResult:
        tr = TaskResult(
            task_id=task.task_id, difficulty=task.difficulty, title=task.title,
            runs=runs,
        )
        if isinstance(client, MockClient):
            client.current_task_dir = task.dir

        issue = task.issue(lang)
        user_prompt = build_user_prompt(issue, task.read_buggy_files())

        attempts = [
            self._one_attempt(
                client, reviewer, task, issue, user_prompt, timeout, retries
            )
            for _ in range(runs)
        ]
        _aggregate_attempts(tr, attempts, self.scoring_cfg)
        tr.usability_tier = usability.classify(
            tr.success_rate, tr.quality_score, self.usability_cfg
        )
        return tr


def _aggregate_attempts(
    tr: TaskResult, attempts: list[Attempt], scoring_cfg: dict
) -> None:
    """複数試行を集計し TaskResult を埋める. runs=1 なら従来値と一致する."""
    n = len(attempts)
    passed = [a for a in attempts if a.resolved]
    c = len(passed)

    tr.n_pass = c
    tr.success_rate = round(c / n, 3) if n else 0.0
    tr.pass_at_1 = tr.success_rate
    tr.pass_at_k = round(pass_at_k(n, c, n), 3)

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

    # 試行ごとの軽量サマリ (JSONに残す)
    tr.attempts = [
        {
            "resolved": a.resolved,
            "quality": round(a.quality_score, 1),
            "combined": a.combined,
            "fail_reason": a.fail_reason,
        }
        for a in attempts
    ]


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
    json_path = output_dir / f"{stamp}_{run.model}_results.json"
    md_path = output_dir / f"{stamp}_{run.model}_report.md"
    artifacts_dir = output_dir / f"{stamp}_{run.model}_artifacts"

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
        "usability": {t: overall.get(t, 0) for t in usability.TIERS},
    }
    if run.multi_run:
        summary["avg_success_rate"] = round(run.avg_success_rate, 3)
        summary["avg_pass_at_k"] = round(run.avg_pass_at_k, 3)

    payload = {
        "model": run.model,
        "issue_lang": run.issue_lang,
        "artifacts_dir": artifacts_dir.name,
        "summary": summary,
        "results": [_lean(r) for r in run.results],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(render_markdown(run), encoding="utf-8")
    return json_path, md_path
