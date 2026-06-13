"""タスクのロード. tasks/tasks.jsonl + 各タスクディレクトリ."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    task_id: str
    difficulty: str          # easy | medium | hard
    title: str
    dir: Path                # tasks/t001_xxx/
    files: list[str]         # buggy_code配下の相対パス一覧

    def issue(self, lang: str = "en") -> str:
        name = "issue_ja.md" if lang == "ja" else "issue.md"
        p = self.dir / name
        if not p.exists():
            p = self.dir / "issue.md"
        return p.read_text(encoding="utf-8")

    def read_buggy_files(self) -> dict[str, str]:
        return {
            f: (self.dir / "buggy_code" / f).read_text(encoding="utf-8")
            for f in self.files
        }


def load_tasks(tasks_root: Path, only: list[str] | None = None) -> list[Task]:
    """tasks.jsonl からタスク一覧をロードする."""
    jsonl = tasks_root / "tasks.jsonl"
    tasks = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        task_dir = tasks_root / rec["dir"]
        files = [
            str(p.relative_to(task_dir / "buggy_code"))
            for p in sorted((task_dir / "buggy_code").rglob("*.py"))
        ]
        t = Task(
            task_id=rec["task_id"],
            difficulty=rec["difficulty"],
            title=rec["title"],
            dir=task_dir,
            files=files,
        )
        if only and t.task_id not in only:
            continue
        tasks.append(t)
    return tasks
