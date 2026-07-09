"""merge_results() の合算ロジックの単体テスト (ネットワーク不要)."""

from __future__ import annotations

import json

from llmbench.certify import certify, merge_results


def _write(tmp_path, name, model, results):
    """results.json を tmp_path に書き、そのパス(str)を返すヘルパ。"""
    p = tmp_path / name
    p.write_text(
        json.dumps({"model": model, "results": results}, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(p)


def test_merge_two_files_combines(tmp_path):
    base = _write(tmp_path, "base.json", "m",
                  [{"task_id": "t001", "difficulty": "easy"}])
    l6 = _write(tmp_path, "l6.json", "m",
                [{"task_id": "a061", "difficulty": "architect"}])
    _, results = merge_results([base, l6])
    ids = {t["task_id"] for t in results}
    assert ids == {"t001", "a061"}
    assert len(results) == 2


def test_merge_dedup_last_wins(tmp_path):
    f1 = _write(tmp_path, "f1.json", "m",
                [{"task_id": "t001", "difficulty": "easy", "combined": 10.0}])
    f2 = _write(tmp_path, "f2.json", "m",
                [{"task_id": "t001", "difficulty": "easy", "combined": 99.0}])
    _, results = merge_results([f1, f2])
    assert len(results) == 1
    assert results[0]["combined"] == 99.0  # 後ファイル優先


def test_merge_model_label_distinct(tmp_path):
    # 同名 -> 単独
    a = _write(tmp_path, "a.json", "modelX", [{"task_id": "t1", "difficulty": "easy"}])
    b = _write(tmp_path, "b.json", "modelX", [{"task_id": "t2", "difficulty": "easy"}])
    label, _ = merge_results([a, b])
    assert label == "modelX"

    # 異名 -> " + " 連結
    c = _write(tmp_path, "c.json", "modelY", [{"task_id": "t3", "difficulty": "easy"}])
    label2, _ = merge_results([a, c])
    assert label2 == "modelX + modelY"


def test_merge_single_file(tmp_path):
    results_in = [
        {"task_id": "t001", "difficulty": "easy", "success_rate": 1.0,
         "combined": 80.0},
    ]
    f = _write(tmp_path, "one.json", "m", results_in)
    label, merged = merge_results([f])
    assert label == "m"
    # 単独 certify と同一判定になる。
    assert certify(merged) == certify(results_in)


def test_merge_missing_task_id_kept(tmp_path):
    f = _write(tmp_path, "f.json", "m", [
        {"task_id": "t001", "difficulty": "easy"},
        {"difficulty": "easy"},  # task_id 無し
    ])
    _, results = merge_results([f])
    assert len(results) == 2
    assert sum(1 for t in results if t.get("task_id") is None) == 1


def test_merge_then_certify_tier_counts(tmp_path):
    # base: L1(easy) success_rate形式 / l6: L6(architect) resolved旧形式 の混在。
    base = _write(tmp_path, "base.json", "m", [
        {"task_id": "t001", "difficulty": "easy", "success_rate": 1.0,
         "combined": 90.0},
        {"task_id": "t002", "difficulty": "easy", "success_rate": 1.0,
         "combined": 90.0},
    ])
    l6 = _write(tmp_path, "l6.json", "m", [
        {"task_id": "a061", "difficulty": "architect", "resolved": True,
         "combined": 70.0},
    ])
    _, merged = merge_results([base, l6])
    cert = certify(merged)
    tiers = {r["tier"]: r for r in cert["tiers"]}
    assert tiers["L1"]["n"] == 2
    assert tiers["L1"]["measured"] is True
    assert tiers["L6"]["n"] == 1
    assert tiers["L6"]["measured"] is True
    # 旧形式 resolved=True は success 1.0 として扱われる。
    assert tiers["L6"]["mean_success"] == 1.0
