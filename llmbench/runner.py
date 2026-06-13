"""ベンチマーク実行オーケストレータ."""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import sandbox
from .clients import LLMClient, create_client
from .clients.mock import MockClient
from .functional import evaluate_functional
from .patch import parse_llm_output
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .quality import evaluate_quality
from .scoring import combined_score
from .tasks import Task, load_tasks


@dataclass
class TaskResult:
    task_id: str
    difficulty: str
    resolved: bool = False
    quality_score: float = 0.0
    combined: float = 0.0
    latency_sec: float = 0.0
    tokens_per_sec: float | None = None
    completion_tokens: int | None = None
    fail_reason: str = ""
    quality_components: dict = field(default_factory=dict)


@dataclass
class RunResult:
    model: str
    issue_lang: str
    results: list[TaskResult] = field(default_factory=list)

    @property
    def resolved_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.resolved for r in self.results) / len(self.results)

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

        tasks = load_tasks(self.tasks_root, only=only_tasks)
        run = RunResult(model=model_name, issue_lang=lang)

        for i, task in enumerate(tasks, 1):
            progress(f"[{i}/{len(tasks)}] {task.task_id} ({task.difficulty}) ...")
            tr = self._run_task(client, reviewer, task, lang, timeout, retries)
            run.results.append(tr)
            status = "RESOLVED" if tr.resolved else f"FAILED ({tr.fail_reason})"
            progress(
                f"    {status}  quality={tr.quality_score:.0f} "
                f"combined={tr.combined:.0f} "
                f"({tr.latency_sec:.1f}s)"
            )
        return run

    def _run_task(
        self,
        client: LLMClient,
        reviewer: LLMClient | None,
        task: Task,
        lang: str,
        timeout: int,
        retries: int,
    ) -> TaskResult:
        tr = TaskResult(task_id=task.task_id, difficulty=task.difficulty)
        if isinstance(client, MockClient):
            client.current_task_dir = task.dir

        issue = task.issue(lang)
        user_prompt = build_user_prompt(issue, task.read_buggy_files())

        # 生成 (+パース失敗時リトライ)
        patch = None
        total_latency = 0.0
        gen = None
        for _attempt in range(retries + 1):
            try:
                gen = client.generate(SYSTEM_PROMPT, user_prompt)
            except Exception as e:
                tr.fail_reason = f"generation error: {e}"
                return tr
            total_latency += gen.latency_sec
            patch = parse_llm_output(gen.text, task.files)
            if patch.parse_ok:
                break
        tr.latency_sec = round(total_latency, 2)
        if gen is not None:
            tr.tokens_per_sec = (
                round(gen.tokens_per_sec, 1) if gen.tokens_per_sec else None
            )
            tr.completion_tokens = gen.completion_tokens

        # 機能評価 (品質評価のためworkspaceを保持)
        func, ws = evaluate_functional(
            task.dir, patch, self.work_root, timeout=timeout, keep_workspace=True
        )
        tr.resolved = func.resolved
        tr.fail_reason = func.fail_reason

        # 品質評価 (patchがファイル適用できた場合のみ)
        try:
            if ws is not None and func.applied_files:
                q = evaluate_quality(
                    ws, func.applied_files, self.quality_cfg,
                    issue_text=issue, reviewer_client=reviewer,
                )
                tr.quality_score = q.score
                tr.quality_components = q.components
        finally:
            if ws is not None:
                sandbox.cleanup(ws)

        tr.combined = combined_score(
            tr.resolved, tr.quality_score, self.scoring_cfg
        )
        return tr


def save_run(run: RunResult, output_dir: Path) -> tuple[Path, Path]:
    """結果をJSONとして保存. (json_path, md_path) を返す."""
    from .report import render_markdown

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{stamp}_{run.model}_results.json"
    md_path = output_dir / f"{stamp}_{run.model}_report.md"

    payload = {
        "model": run.model,
        "issue_lang": run.issue_lang,
        "summary": {
            "resolved_rate": round(run.resolved_rate, 3),
            "avg_quality_resolved": round(run.avg_quality_resolved, 1),
            "avg_combined": round(run.avg_combined, 1),
            "n_tasks": len(run.results),
        },
        "results": [asdict(r) for r in run.results],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(render_markdown(run), encoding="utf-8")
    return json_path, md_path
