"""出力が空/打ち切りの試行は detection で必ず不合格になること (デコイ含む)."""
from __future__ import annotations

import pathlib

import pytest

from llmbench.graders import GradeCtx
from llmbench.graders.detection import DetectionGrader
from llmbench.tasks import load_tasks

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _task(tid: str, ledger: str = "tasks_sec.jsonl"):
    return load_tasks(ROOT / "tasks", only=[tid], ledgers=[ledger])[0]


def _ctx():
    return GradeCtx(work_root=ROOT, graders_cfg={"detection": {
        "pass_f1": 0.67, "pass_recall": 0.6, "max_fp_per_gold": 1.0,
        "location_weight": 0.3}})


@pytest.mark.parametrize("tid", ["s04", "s10", "s12", "s15", "s16", "s17"])
@pytest.mark.parametrize("raw", ["", "   \n", "<think>still thinking about whether this is safe"])
def test_decoy_without_output_fails(tid, raw):
    ev = DetectionGrader().evaluate(_task(tid), raw, _ctx())
    assert ev.parse_ok is False
    assert ev.resolved is False
    assert ev.quality_score == 0.0
    assert ev.fail_reason.startswith("no findings output")


@pytest.mark.parametrize("tid", ["s04", "s16"])
def test_decoy_explicit_empty_array_still_passes(tid):
    ev = DetectionGrader().evaluate(_task(tid), "--- FINDINGS ---\n[]", _ctx())
    assert ev.parse_ok is True
    assert ev.resolved is True


def test_real_task_without_output_fails():
    ev = DetectionGrader().evaluate(_task("s14"), "", _ctx())
    assert ev.resolved is False
    assert ev.fail_reason.startswith("no findings output")
