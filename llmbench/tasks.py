"""タスクのロード. tasks/tasks.jsonl + 各タスクディレクトリ."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .graders import GRADER_DOMAIN


@dataclass
class Task:
    task_id: str
    difficulty: str          # easy | medium | hard ... | sec_* | gen_* | med_* 等
    title: str
    dir: Path                # tasks/t001_xxx/
    files: list[str]         # buggy_code配下の相対パス一覧
    perf_timeout: int | None = None  # 性能制約タスク用の個別タイムアウト(秒)
    grader: str = "code"     # code | detection | constraint | judge | qa
    domain: str = "code"     # code | security | general | writing | medical

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


def load_tasks(
    tasks_root: Path,
    only: list[str] | None = None,
    ledgers: list[str] | None = None,
) -> list[Task]:
    """1つ以上の台帳(jsonl)からタスク一覧をロードする.

    ledgers 省略時は ["tasks.jsonl"] のみ。L6 などの任意 tier を上乗せする場合は
    ["tasks.jsonl", "tasks_l6.jsonl"] のように渡す。重複 task_id は先勝ち。
    """
    ledgers = ledgers or ["tasks.jsonl"]
    tasks = []
    seen: set[str] = set()
    for ledger in ledgers:
        jsonl = tasks_root / ledger
        if not jsonl.exists():
            continue
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            task_dir = tasks_root / rec["dir"]
            # buggy_code が無いドメインタスク (detection/constraint/judge/qa) を許容する
            bc = task_dir / "buggy_code"
            files = (
                [str(p.relative_to(bc)) for p in sorted(bc.rglob("*.py"))]
                if bc.exists() else []
            )
            grader = rec.get("grader", "code")
            t = Task(
                task_id=rec["task_id"],
                difficulty=rec["difficulty"],
                title=rec["title"],
                dir=task_dir,
                files=files,
                perf_timeout=rec.get("perf_timeout"),
                grader=grader,
                domain=rec.get("domain") or GRADER_DOMAIN.get(grader, "code"),
            )
            if only and t.task_id not in only:
                continue
            if t.task_id in seen:
                continue
            seen.add(t.task_id)
            tasks.append(t)
    return tasks
