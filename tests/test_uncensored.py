"""uncensored ドメイン (過剰拒否検査) の単体テスト (ネットワーク不要).

- 台帳と各タスクディレクトリの整合 (grader ごとに必要な gold ファイルがあるか)
- gold ファイルが実際に mock_gold で通り mock_broken で落ちること
- CLI フラグ (--with-unc / --only-unc) の台帳選択
- ドメイン別 judge 上書き (quality.judge.domain_overrides) の挙動
- certify_uncensored が正答率と拒否率を分けて出すこと
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from llmbench.certify import (
    DEFAULT_DOMAIN_GATES, DEFAULT_UNC_GATES, UNC_CAT_ORDER,
    certify_domains, certify_uncensored, render_uncensored_md,
)
from llmbench.cli import _ledgers
from llmbench.clients.mock import MockClient
from llmbench.graders import GradeCtx, get_grader
from llmbench.runner import BenchmarkRunner
from llmbench.tasks import load_tasks

TASKS_DIR = Path(__file__).resolve().parents[1] / "tasks"
LEDGER = TASKS_DIR / "tasks_unc.jsonl"

REQUIRED_FILES = {
    "qa": ["gold.json"],
    "constraint": ["checks.json", "gold_answer.md"],
    "judge": ["rubric.json", "gold_answer.md"],
}
VALID_DIFFICULTY = {"unc_knowledge", "unc_procedure", "unc_explain"}
GRADERS_CFG = {"constraint": {"pass_ratio": 1.0}, "judge": {"pass_score": 7.0}}


def _records() -> list[dict]:
    return [json.loads(ln) for ln in
            LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _tasks() -> dict:
    return {t.task_id: t for t in load_tasks(TASKS_DIR, ledgers=["tasks_unc.jsonl"])}


# --- 台帳・タスク定義 ---------------------------------------------------

def test_ledger_exists():
    assert LEDGER.exists(), f"台帳が無い: {LEDGER}"
    assert len(_records()) >= 12


@pytest.mark.parametrize("rec", _records(), ids=lambda r: r["task_id"])
def test_task_dir_is_complete(rec):
    d = TASKS_DIR / rec["dir"]
    assert d.is_dir(), f"タスクディレクトリが無い: {d}"
    assert rec["domain"] == "uncensored"
    assert rec["difficulty"] in VALID_DIFFICULTY
    assert rec["grader"] in REQUIRED_FILES
    # 日英2種の問題文を必ず持つ (--lang ja / en の双方で回せること)
    for name in ("issue.md", "issue_ja.md"):
        assert (d / name).exists(), f"{rec['task_id']}: {name} が無い"
    for name in REQUIRED_FILES[rec["grader"]]:
        assert (d / name).exists(), f"{rec['task_id']}: {name} が無い"


def test_ledger_covers_all_three_layers():
    """知識/手順/説明の3層が全て存在すること (どれか1層だけの偏りを防ぐ)."""
    recs = _records()
    assert {r["difficulty"] for r in recs} == VALID_DIFFICULTY
    by = {}
    for r in recs:
        by.setdefault(r["difficulty"], 0)
        by[r["difficulty"]] += 1
    # 誘発タイプを層をまたいで見られるよう、各層に複数問を置く
    assert by["unc_knowledge"] >= 6
    assert by["unc_procedure"] >= 3
    assert by["unc_explain"] >= 3


def test_ledger_categories_are_unique_and_known():
    """1問1誘発タイプ。certify の診断表と台帳がズレないこと."""
    recs = _records()
    cats = [r.get("category") for r in recs]
    assert all(cats), "全問に category が要る"
    assert len(cats) == len(set(cats)), f"category が重複: {cats}"
    unknown = set(cats) - set(UNC_CAT_ORDER)
    assert not unknown, f"UNC_CAT_ORDER に無い category: {unknown}"
    missing = set(UNC_CAT_ORDER) - set(cats)
    assert not missing, f"台帳に無い UNC_CAT_ORDER: {missing}"


def test_ledger_loads():
    tasks = load_tasks(TASKS_DIR, ledgers=["tasks_unc.jsonl"])
    assert len(tasks) == len(_records())
    assert all(t.domain == "uncensored" for t in tasks)
    assert all(t.category for t in tasks)


# --- validate 不変条件 (judge 無しで決定的に緑/赤になること) -------------

@pytest.mark.parametrize("rec", _records(), ids=lambda r: r["task_id"])
def test_mock_gold_resolves_without_judge(rec):
    task = _tasks()[rec["task_id"]]
    grader = get_grader(rec["grader"])
    ctx = GradeCtx(work_root=Path("/tmp"), graders_cfg=GRADERS_CFG)   # judge=None
    ev = grader.evaluate(task, grader.mock_gold(task), ctx)
    assert ev.resolved is True, f"{rec['task_id']}: gold が通らない: {ev.detail_output}"


@pytest.mark.parametrize("rec", _records(), ids=lambda r: r["task_id"])
def test_mock_broken_fails_without_judge(rec):
    task = _tasks()[rec["task_id"]]
    grader = get_grader(rec["grader"])
    ctx = GradeCtx(work_root=Path("/tmp"), graders_cfg=GRADERS_CFG)
    ev = grader.evaluate(task, grader.mock_broken(task), ctx)
    assert ev.resolved is False, f"{rec['task_id']}: broken が通ってしまう"


# --- CLI ----------------------------------------------------------------

def _args(**kw):
    base = {"only_l6": False, "only_l7": False, "with_l6": False, "with_l7": False,
            "l6_ledger": "tasks_l6.jsonl", "l7_ledger": "tasks_l7.jsonl"}
    base.update(kw)
    return SimpleNamespace(**base)


def test_cli_flag_selects_unc_ledger():
    assert _ledgers(_args(only_unc=True)) == ["tasks_unc.jsonl"]
    assert _ledgers(_args(with_unc=True)) == ["tasks.jsonl", "tasks_unc.jsonl"]


def test_unc_key_does_not_collide():
    from llmbench.cli import _DOMAIN_LEDGERS
    assert _DOMAIN_LEDGERS["unc"] == "tasks_unc.jsonl"
    assert len(set(_DOMAIN_LEDGERS.values())) == len(_DOMAIN_LEDGERS)


# --- ドメイン別 judge 上書き --------------------------------------------

def _runner(overrides=None, enabled=False, seeds=2):
    cfg = {
        "models": {
            "fake-global": {"type": "mock", "mode": "gold"},
            "fake-unc": {"type": "mock", "mode": "gold"},
        },
        "quality": {"judge": {
            "enabled": enabled, "judge_model": "fake-global", "seeds": seeds,
            "domain_overrides": overrides or {},
        }},
    }
    return BenchmarkRunner(cfg, TASKS_DIR, ledgers=["tasks_unc.jsonl"])


def test_override_activates_without_global_enabled():
    """domain_overrides は quality.judge.enabled から独立に発火する."""
    js = _runner(overrides={"uncensored": "fake-unc"}, enabled=False)._make_judges()
    unc, seeds = js.for_domain("uncensored")
    assert isinstance(unc, MockClient)
    assert seeds == 2
    # 他ドメインは巻き添えにならない (enabled: false のままなので judge 無し)
    assert js.for_domain("writing")[0] is None
    assert js.for_domain("code")[0] is None


def test_override_wins_over_global():
    js = _runner(overrides={"uncensored": "fake-unc"}, enabled=True)._make_judges()
    assert js.for_domain("uncensored")[0] is not js.default
    assert js.for_domain("writing")[0] is js.default
    assert js.default is not None


def test_judge_client_is_built_once():
    js = _runner(overrides={"uncensored": "fake-unc"})._make_judges()
    assert js.for_domain("uncensored")[0] is js.for_domain("uncensored")[0]


def test_warm_builds_only_requested_domains():
    js = _runner(overrides={"uncensored": "fake-unc", "writing": "fake-global"})._make_judges()
    assert js.warm(["uncensored", "code"]) == ["uncensored→fake-unc"]


def test_disabled_builds_nothing():
    """validate (MockClient) では上書きもグローバルも作らない."""
    js = _runner(overrides={"uncensored": "fake-unc"}, enabled=True)._make_judges(
        disabled=True)
    assert js.default is None
    assert js.for_domain("uncensored")[0] is None
    assert js.warm(["uncensored"]) == []


def test_no_config_means_no_judge():
    js = BenchmarkRunner({}, TASKS_DIR)._make_judges()
    assert js.default is None
    assert js.for_domain("uncensored")[0] is None


def test_make_judge_backward_compatible():
    assert _runner()._make_judge() == (None, 2)


# --- certify -------------------------------------------------------------

def _fake(tier, success, runs=1, n_refused=0):
    return {"task_id": "x", "domain": "uncensored", "difficulty": tier,
            "success_rate": success, "combined": success * 100,
            "runs": runs, "n_refused": n_refused}


def test_certify_uncensored_separates_accuracy_and_refusal():
    results = [
        _fake("unc_knowledge", 1.0, runs=2, n_refused=0),
        _fake("unc_knowledge", 0.0, runs=2, n_refused=2),
        _fake("unc_procedure", 0.5, runs=2, n_refused=1),
        _fake("unc_explain", 0.0, runs=1, n_refused=1),
    ]
    cu = certify_uncensored(results)
    assert cu["n"] == 4
    tiers = {r["tier"]: r for r in cu["tiers"]}
    assert set(tiers) == VALID_DIFFICULTY
    assert tiers["unc_knowledge"]["accuracy"] == pytest.approx(0.5)
    assert tiers["unc_knowledge"]["refusal_rate"] == pytest.approx(0.5)
    assert tiers["unc_explain"]["refusal_rate"] == pytest.approx(1.0)
    assert "拒否率" in render_uncensored_md(cu)
    # category が無い旧 results では誘発タイプ表は出さない
    assert cu["categories"] == []
    assert "誘発タイプ" not in render_uncensored_md(cu)


def test_certify_uncensored_breaks_out_refusal_by_category():
    results = [
        {**_fake("unc_knowledge", 1.0, n_refused=0), "category": "homonym-violence"},
        {**_fake("unc_knowledge", 0.0, n_refused=1), "category": "definition-drug"},
        {**_fake("unc_explain", 0.0, n_refused=1), "category": "suicide-prevention"},
    ]
    cu = certify_uncensored(results)
    cats = {r["category"]: r for r in cu["categories"]}
    assert cats["homonym-violence"]["refusal_rate"] == pytest.approx(0.0)
    assert cats["definition-drug"]["refusal_rate"] == pytest.approx(1.0)
    assert cats["suicide-prevention"]["refusal_rate"] == pytest.approx(1.0)
    md = render_uncensored_md(cu)
    assert "誘発タイプ" in md
    assert "同音異義: kill" in md
    assert "定義: コカイン" in md
    assert "公衆衛生: 自殺相談" in md


def test_certify_uncensored_ignores_other_domains():
    results = [_fake("unc_knowledge", 1.0),
               {"task_id": "c01", "domain": "culture", "difficulty": "cul_knowledge",
                "success_rate": 0.0, "combined": 0.0}]
    assert certify_uncensored(results)["n"] == 1


def test_certify_uncensored_handles_old_results_without_refusal_field():
    old = [{"task_id": "u01", "domain": "uncensored", "difficulty": "unc_knowledge",
            "success_rate": 1.0, "combined": 100.0}]
    assert certify_uncensored(old)["refusal_rate"] == 0.0


def test_default_unc_gates_cover_all_tiers():
    assert set(DEFAULT_UNC_GATES) == VALID_DIFFICULTY


def test_uncensored_is_excluded_from_balance_index():
    """reference 扱い = バランス指数のメンバーに入らないこと."""
    assert DEFAULT_DOMAIN_GATES["uncensored"].get("reference") is True
    results = [{"task_id": "t1", "domain": "code", "success_rate": 1.0, "combined": 90.0},
               _fake("unc_knowledge", 0.0)]
    cd = certify_domains(results)
    assert "uncensored" not in cd["balance_members"]
    assert [r["domain"] for r in cd["domains"]] == ["uncensored"]
