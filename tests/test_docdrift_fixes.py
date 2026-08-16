"""監査で確定した不具合の回帰テスト (ネットワーク不要).

対象は certify の累積判定 / 合否文言 / ゲート差し替え、save_run のファイル名
サニタイズ、load_tasks の台帳欠落検出、pass@k の k 指定、grader ドメイン整合。
いずれも既存テストに守られていなかった箇所。
"""

from __future__ import annotations

import json

import pytest

from llmbench.certify import (
    certify,
    certify_domains,
    certify_medical,
    render_certificate_md,
)
from llmbench.graders import GRADER_DOMAIN, check_domains, get_grader
from llmbench.runner import (
    Attempt,
    RunResult,
    TaskResult,
    _aggregate_attempts,
    _safe_label,
    save_run,
)
from llmbench.tasks import load_tasks


def _task(task_id, difficulty, success, combined, domain="code"):
    return {
        "task_id": task_id, "difficulty": difficulty, "domain": domain,
        "success_rate": success, "combined": combined,
    }


# ===== 1. 累積到達レベル (未測定tierで打ち切る) =====


def test_cumulative_l7_only_is_undecidable():
    """L7 だけ測って合格しても、L1 が未測定なら累積判定は不能。"""
    cert = certify([_task("t063", "grandmaster", 1.0, 90.0)])
    assert cert["achieved_level"] is None
    assert cert["cumulative_blocked_by"] == ("L1", "unmeasured")
    # 独立判定では L7 合格として残る (累積とは別軸)。
    assert cert["independent_pass"] == ["L7"]
    assert cert["verdict"] == "累積判定は不能(L1 が未測定)。独立判定を参照。"


def test_cumulative_l1_only_pass():
    """L1 だけ合格 → 到達 L1、以降は L2 が未測定で打ち切り。"""
    cert = certify([_task("t001", "easy", 1.0, 90.0)])
    assert cert["achieved_level"] == "L1"
    assert cert["cumulative_blocked_by"] == ("L2", "unmeasured")


def test_cumulative_l1_to_l4_all_pass():
    """L1〜L4 を連続合格 → 到達 L4。打ち切りは L5 の未測定。"""
    cert = certify([
        _task("t001", "easy", 1.0, 95.0),
        _task("t002", "medium", 1.0, 95.0),
        _task("t003", "hard", 1.0, 95.0),
        _task("t004", "expert", 1.0, 95.0),
    ])
    assert cert["achieved_level"] == "L4"
    assert cert["cumulative_blocked_by"] == ("L5", "unmeasured")
    assert cert["usable_line"] is True


def test_cumulative_l1_gate_fail():
    """L1 を測って落ちた場合は unmeasured ではなく gate_fail。"""
    cert = certify([_task("t001", "easy", 0.1, 10.0)])
    assert cert["achieved_level"] is None
    assert cert["cumulative_blocked_by"] == ("L1", "gate_fail")
    assert "判定不能" not in cert["verdict"]


# ===== 2. render_certificate_md の合否文言 3ケース =====


def test_render_l4_pass_text():
    cert = certify([
        _task("t001", "easy", 1.0, 95.0),
        _task("t004", "expert", 1.0, 95.0),
    ])
    md = render_certificate_md(cert, "m")
    assert "✅ 使えるライン到達** (L4 expert を独立に合格)" in md


def _verdict_line(md: str) -> str:
    """主判定 (使えるライン) の1行を取り出す。脚注の定型文と区別するため。"""
    return next(ln for ln in md.splitlines() if "使えるライン" in ln and "**" in ln)


def test_render_l4_fail_text():
    cert = certify([_task("t004", "expert", 0.0, 0.0)])
    line = _verdict_line(render_certificate_md(cert, "m"))
    assert line == "**❌ 使えるライン未到達** (L4 expert を独立に不合格)"
    # 旧実装は不合格でも「(L4 expert を独立に合格)」と出していた。
    assert "独立に合格" not in line


def test_render_l4_unmeasured_text():
    """L7 だけの結果: L4 未測定・累積は判定不能と明示される。"""
    cert = certify([_task("t063", "grandmaster", 1.0, 90.0)])
    md = render_certificate_md(cert, "m")
    assert "❌ 使えるライン未到達** (L4 expert は未測定のため判定不能)" in md
    # L1未達 (実際に測って落ちた) と取り違えさせない。
    assert "累積到達レベル **判定不能 (L1 が未測定)**" in md
    assert "なし (L1未達)" not in md


# ===== 3. certify_domains / certify_medical のゲート差し替え =====


def test_certify_domains_uses_passed_gates():
    results = [_task("g1", "gen_std", 0.65, 62.0, domain="general")]
    # 既定 (0.70/65.0) では不合格。
    assert certify_domains(results)["domains"][0]["gate_pass"] is False
    # 渡したゲート (0.60/60.0) では合格。
    loose = {"general": {"min_success": 0.60, "min_combined": 60.0}}
    assert certify_domains(results, loose)["domains"][0]["gate_pass"] is True


def test_certify_medical_uses_passed_gates():
    results = [_task("m1", "med_std", 0.50, 50.0, domain="medical")]
    # 既定 med_std=0.60 では不合格。
    default_row = certify_medical(results)["tiers"][0]
    assert default_row["gate"] == 0.60
    assert default_row["pass"] is False
    # 渡したゲート 0.40 では合格。
    row = certify_medical(results, {"med_std": 0.40})["tiers"][0]
    assert row["gate"] == 0.40
    assert row["pass"] is True


# ===== 4. _safe_label =====


@pytest.mark.parametrize("raw,expected", [
    ("hf.co/unsloth/Qwen3-Coder-GGUF:Q4_K_M", "Qwen3-Coder-GGUF-Q4_K_M"),
    ("qwen2.5-coder:32b", "qwen2.5-coder-32b"),
    ("plain-model", "plain-model"),
    (r"C:\models\foo.gguf", "foo.gguf"),
    ('a<b>c:d"e|f?g*h', "a-b-c-d-e-f-g-h"),
    ("", "model"),
    (".", "model"),
    ("...", "model"),
    ("   ", "model"),
    ("  .name.  ", "name"),
])
def test_safe_label(raw, expected):
    out = _safe_label(raw)
    assert out == expected
    assert "/" not in out and "\\" not in out
    assert out  # 空文字にならない


# ===== 5. save_run: スラッシュ入りモデル名 =====


def test_save_run_with_slash_in_model_name(tmp_path):
    model = "hf.co/unsloth/Qwen3-Coder-GGUF:Q4_K_M"
    run = RunResult(model=model, issue_lang="en", results=[
        TaskResult(task_id="t001", difficulty="easy", title="x", resolved=True),
    ])
    json_path, md_path = save_run(run, tmp_path)

    assert json_path.exists() and md_path.exists()
    # ファイル名にスラッシュ由来のサブディレクトリを作っていない。
    assert json_path.parent == tmp_path
    assert "/" not in json_path.name
    # results.json の model は原文のまま (既存結果との継続性)。
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["model"] == model


def test_save_run_pass_k_field_present(tmp_path):
    """項目8: results.json に pass_k が載る (既定は runs と同値)。"""
    tr = TaskResult(task_id="t001", difficulty="easy", title="x")
    _aggregate_attempts(tr, [Attempt(resolved=True)], {})
    run = RunResult(model="m", issue_lang="en", results=[tr])
    json_path, _ = save_run(run, tmp_path)
    rec = json.loads(json_path.read_text(encoding="utf-8"))["results"][0]
    assert rec["pass_k"] == 1


# ===== 6. load_tasks の台帳欠落検出 =====


def _write_ledger(dirpath, name, task_ids):
    (dirpath / name).write_text(
        "\n".join(
            json.dumps({"task_id": t, "difficulty": "easy",
                        "title": t, "dir": t})
            for t in task_ids
        ),
        encoding="utf-8",
    )
    for t in task_ids:
        (dirpath / t).mkdir(exist_ok=True)


def test_load_tasks_all_ledgers_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        load_tasks(tmp_path, ledgers=["tasks_l7_TYPO.jsonl"])
    msg = str(ei.value)
    assert "tasks_l7_TYPO.jsonl" in msg
    assert "--l7-ledger" in msg


def test_load_tasks_partial_missing_warns_and_continues(tmp_path, capsys):
    _write_ledger(tmp_path, "tasks.jsonl", ["t001"])
    tasks = load_tasks(tmp_path, ledgers=["tasks.jsonl", "tasks_missing.jsonl"])
    assert [t.task_id for t in tasks] == ["t001"]
    assert "tasks_missing.jsonl" in capsys.readouterr().err


def test_load_tasks_unknown_only_id_raises(tmp_path):
    """`only` の task_id が台帳に無ければ例外にする.

    旧挙動は「台帳は読めているので0件で正常終了」だったが、これが実害を出した:
    L7 のタスクIDを --with-l7 無しで指定すると、1問も実行されないまま
    resolved_rate=0.0 の results.json が保存され、全問失敗と区別できなかった。
    """
    _write_ledger(tmp_path, "tasks.jsonl", ["t001"])
    with pytest.raises(ValueError) as ei:
        load_tasks(tmp_path, only=["tXXX"], ledgers=["tasks.jsonl"])
    msg = str(ei.value)
    assert "tXXX" in msg and "--with-l7" in msg


def test_load_tasks_partial_unknown_only_id_raises(tmp_path):
    """一部だけ見つからない場合も、見つからなかったIDを名指しで報せる."""
    _write_ledger(tmp_path, "tasks.jsonl", ["t001", "t002"])
    with pytest.raises(ValueError) as ei:
        load_tasks(tmp_path, only=["t001", "t069"], ledgers=["tasks.jsonl"])
    assert "t069" in str(ei.value) and "t001" not in str(ei.value).split("見つかりません")[1].split(chr(10))[0]


def test_load_tasks_only_all_found_is_ok(tmp_path):
    _write_ledger(tmp_path, "tasks.jsonl", ["t001", "t002"])
    got = load_tasks(tmp_path, only=["t002"], ledgers=["tasks.jsonl"])
    assert [t.task_id for t in got] == ["t002"]


def test_load_tasks_strict_false_allows_all_missing(tmp_path):
    assert load_tasks(tmp_path, ledgers=["nope.jsonl"], strict=False) == []


# ===== 7. pass@k の k 指定 =====


def _attempts(n, c):
    return [Attempt(resolved=(i < c)) for i in range(n)]


def test_pass_at_k_default_matches_legacy():
    """pass_k 未指定 → k=runs。従来どおり 0/1 に退化する。"""
    tr = TaskResult(task_id="t", difficulty="easy")
    _aggregate_attempts(tr, _attempts(5, 2), {})
    assert tr.pass_k == 5
    assert tr.pass_at_k == 1.0     # c>=1 なら常に 1.0 (= solved_any)
    assert tr.success_rate == 0.4  # pass@1 は影響を受けない

    tr0 = TaskResult(task_id="t", difficulty="easy")
    _aggregate_attempts(tr0, _attempts(5, 0), {})
    assert tr0.pass_at_k == 0.0


def test_pass_at_k_with_k_less_than_runs():
    """k=2 / runs=5 / c=2 → 1 - C(3,2)/C(5,2) = 1 - 3/10 = 0.7。"""
    tr = TaskResult(task_id="t", difficulty="easy")
    _aggregate_attempts(tr, _attempts(5, 2), {}, k=2)
    assert tr.pass_k == 2
    assert tr.pass_at_k == 0.7


def test_pass_at_k_clamped_to_runs():
    """k > runs は runs にクランプされる (0/1 退化と同じ)。"""
    tr = TaskResult(task_id="t", difficulty="easy")
    _aggregate_attempts(tr, _attempts(3, 1), {}, k=99)
    assert tr.pass_k == 3
    assert tr.pass_at_k == 1.0


# ===== 8. grader ドメイン整合 =====


def test_grader_domain_matches_registry():
    """全 grader の Grader.domain が GRADER_DOMAIN と一致すること."""
    assert check_domains() == {}


@pytest.mark.parametrize("name", sorted(GRADER_DOMAIN))
def test_each_grader_domain(name):
    assert get_grader(name).domain == GRADER_DOMAIN[name]


def test_qa_grader_domain_is_medical():
    """医療QAが general ゲートで誤判定されないこと (回帰)."""
    assert get_grader("qa").domain == "medical"
