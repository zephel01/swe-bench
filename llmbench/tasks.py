"""タスクのロード. tasks/tasks.jsonl + 各タスクディレクトリ."""

from __future__ import annotations

import json
import sys
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
    strict: bool = True,
) -> list[Task]:
    """1つ以上の台帳(jsonl)からタスク一覧をロードする.

    ledgers 省略時は ["tasks.jsonl"] のみ。L6 などの任意 tier を上乗せする場合は
    ["tasks.jsonl", "tasks_l6.jsonl"] のように渡す。重複 task_id は先勝ち。

    strict=True (既定) のとき、**台帳が1つも読めず、かつ欠落があった**場合は
    FileNotFoundError を送出する。台帳名のタイポ (`--l7-ledger tasks_l7_TYPO.jsonl`)
    が「0タスクで正常終了・resolved_rate=0.0」として保存され、全問失敗と
    見分けがつかなくなるのを防ぐ。
    一部だけ欠落した場合は警告を出して続行する (既定台帳を置かずドメイン台帳
    だけで運用する構成を許容するため)。
    `only` で指定した task_id が読み込んだ台帳に**1つも存在しない**場合も
    ValueError を送出する。L7 のタスクIDを `--with-l7` 無しで指定すると
    「0タスクで正常終了・resolved_rate=0.0」になり、全問失敗と見分けが
    つかなくなるため (実害あり: 2026-08-16)。
    """
    ledgers = ledgers or ["tasks.jsonl"]
    tasks = []
    seen: set[str] = set()
    missing: list[Path] = []
    loaded = 0
    for ledger in ledgers:
        jsonl = tasks_root / ledger
        if not jsonl.exists():
            missing.append(jsonl)
            continue
        loaded += 1
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

    # 指定した task_id が台帳に無い = 台帳の指定漏れ (--with-l7 等) がほぼ確実。
    # 黙って0件にすると「モデルが全問落とした」ランとして保存されてしまう。
    if only:
        requested = [t.strip() for t in only if str(t).strip()]
        found = {t.task_id for t in tasks}
        unknown = [t for t in requested if t not in found]
        if unknown:
            raise ValueError(
                "指定したタスクIDが台帳に見つかりません: "
                + ", ".join(unknown)
                + f"\n  読み込んだ台帳: {', '.join(ledgers)}"
                + "\n  L7 (grandmaster) のタスクは --with-l7 / --only-l7、"
                "L6 (architect) は --with-l6 / --only-l6 が必要です。"
            )

    if missing:
        paths = ", ".join(str(p) for p in missing)
        if loaded == 0 and strict:
            raise FileNotFoundError(
                f"台帳が1つも見つかりません: {paths}\n"
                f"  --tasks-dir (現在: {tasks_root}) と "
                f"--l6-ledger / --l7-ledger のファイル名を確認してください。"
            )
        print(f"⚠️  台帳が見つかりません (スキップ): {paths}", file=sys.stderr)
    return tasks
