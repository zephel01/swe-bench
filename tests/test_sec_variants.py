"""摂動変種 (tasks_sec_aug.jsonl) の整合性テスト (ネットワーク不要)."""

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
TASKS = ROOT / "tasks"
FENCE = re.compile(r"```(python|text)\n(.*?)```", re.S)


def _rows():
    p = TASKS / "tasks_sec_aug.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_every_base_task_has_two_variants():
    base = [json.loads(l) for l in
            (TASKS / "tasks_sec.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {r["task_id"] for r in _rows()}
    for b in base:
        assert f"{b['task_id']}a" in ids, f"{b['task_id']}: 語彙摂動の変種が無い"
        assert f"{b['task_id']}b" in ids, f"{b['task_id']}: 囮追加の変種が無い"


def test_variant_files_exist_and_code_parses():
    for r in _rows():
        d = TASKS / r["dir"]
        for f in ("issue.md", "issue_ja.md", "gold.json"):
            assert (d / f).exists(), f"{r['task_id']}: {f} が無い"
        m = FENCE.search((d / "issue.md").read_text(encoding="utf-8"))
        assert m, f"{r['task_id']}: コードブロックが無い"
        if m.group(1) == "python":
            ast.parse(m.group(2))          # 構文が壊れていないこと


def test_gold_terms_survive_renaming():
    """置換後も gold の識別子が本文に残っていること (置換漏れ検出)."""
    for r in _rows():
        d = TASKS / r["dir"]
        gold = json.loads((d / "gold.json").read_text(encoding="utf-8"))
        for lang in ("issue.md", "issue_ja.md"):
            low = (d / lang).read_text(encoding="utf-8").lower()
            for f in gold.get("findings", []):
                assert any(str(t).lower() in low for t in f["any_of"]), \
                    f"{r['task_id']}/{lang}: {f['id']} の any_of が本文に無い"
                loc = f.get("location_any_of") or []
                if loc:
                    assert any(str(t).lower() in low for t in loc), \
                        f"{r['task_id']}/{lang}: {f['id']} の location_any_of が本文に無い"


def test_variant_a_actually_changed_the_text():
    """語彙摂動が実際に本文を変えていること (無変換のコピーを弾く)."""
    base = {json.loads(l)["task_id"]: json.loads(l)["dir"] for l in
            (TASKS / "tasks_sec.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    for r in _rows():
        if not r["task_id"].endswith("a"):
            continue
        b = TASKS / base[r["task_id"][:-1]] / "issue.md"
        v = TASKS / r["dir"] / "issue.md"
        assert b.read_text(encoding="utf-8") != v.read_text(encoding="utf-8"), \
            f"{r['task_id']}: 語彙摂動で本文が変わっていない"


def test_variant_b_adds_only_safe_decoys():
    """囮追加の変種は gold を変えていないこと."""
    base = {json.loads(l)["task_id"]: json.loads(l)["dir"] for l in
            (TASKS / "tasks_sec.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    for r in _rows():
        if not r["task_id"].endswith("b"):
            continue
        b = json.loads((TASKS / base[r["task_id"][:-1]] / "gold.json").read_text(encoding="utf-8"))
        v = json.loads((TASKS / r["dir"] / "gold.json").read_text(encoding="utf-8"))
        assert b == v, f"{r['task_id']}: 囮追加なのに gold が変わっている"
