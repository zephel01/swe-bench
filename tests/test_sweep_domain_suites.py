"""tools/sweep.sh のドメインスイート (sec/secaug/...) とスイート別思考上限 (ネットワーク不要)."""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SWEEP = ROOT / "tools" / "sweep.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash が必要")


def _run(tmp_path, conf: str, *args, env_extra=None):
    (tmp_path / "models").mkdir(exist_ok=True)
    (tmp_path / "models" / "M-Q.gguf").write_bytes(b"")
    c = tmp_path / "t.conf"
    c.write_text(
        f'MODEL_DIR="{tmp_path}/models"\nMODEL_PREFIX=M\nQUANTS=Q\n'
        f'OUT_ROOT="{tmp_path}/out"\nRESULTS_DIR="{tmp_path}/results"\n'
        "RUN_L6=0; RUN_L7=0; RUN_CULTURE=0; RUN_UNC=0\n" + conf,
        encoding="utf-8",
    )
    env = {**os.environ, "NO_COLOR": "1", **(env_extra or {})}
    return subprocess.run(["bash", str(SWEEP), "-c", str(c), *args],
                          capture_output=True, text=True, env=env, timeout=60)


def test_list_shows_domain_suites_and_reasoning(tmp_path):
    r = _run(tmp_path, "RUN_SEC=1; RUNS_SEC=2\nRUN_SECAUG=1\nREASONING_MAX_TOKENS_SEC=32768\n", "--list")
    assert r.returncode == 0, r.stderr
    assert "sec      runs=2   --only-sec   [reasoning_max_tokens=32768]" in r.stdout
    assert "secaug   runs=3   --only-secaug" in r.stdout


def test_old_suite_order_still_runs_enabled_domain_suite(tmp_path):
    r = _run(tmp_path, 'RUN_SEC=1\nSUITE_ORDER="l6 l7 culture unc"\n', "--list")
    assert r.returncode == 0, r.stderr
    assert "--only-sec" in r.stdout
    assert "末尾に追加" in r.stderr


def test_unknown_suite_fails(tmp_path):
    r = _run(tmp_path, "", "--suites", "nope", "--list")
    assert r.returncode != 0
    assert "未知のスイート 'nope'" in r.stderr + r.stdout


def test_dry_run_writes_suite_config_only_for_that_suite(tmp_path):
    r = _run(tmp_path, "RUN_SEC=1\nRUN_SECAUG=1\nREASONING_MAX_TOKENS_SEC=32768\n", "--dry-run")
    assert r.returncode == 0, r.stderr + r.stdout
    cfgs = sorted((tmp_path / "out").glob("config_*_SEC_r32768.yaml"))
    assert len(cfgs) == 1
    models = yaml.safe_load(cfgs[0].read_text(encoding="utf-8"))["models"]
    assert models["local-openai"]["reasoning_max_tokens"] == 32768
    base = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["models"]
    for k, v in base.items():   # 他のモデルブロックは触らない
        if k != "local-openai":
            assert models[k] == v
    assert f"--config {cfgs[0]}" in r.stdout and "--only-sec" in r.stdout
    assert "Q-secaug" in r.stdout


def test_reasoning_key_added_when_model_block_lacks_it(tmp_path):
    base = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["models"]
    key = next(k for k, v in base.items() if isinstance(v, dict) and "reasoning_max_tokens" not in v
               and v.get("type") == "openai")
    r = _run(tmp_path, f"MODEL_KEY={key}\nRUN_SEC=1\nREASONING_MAX_TOKENS_SEC=20000\n", "--dry-run")
    assert r.returncode == 0, r.stderr + r.stdout
    cfg = next((tmp_path / "out").glob("config_*_SEC_r20000.yaml"))
    assert yaml.safe_load(cfg.read_text(encoding="utf-8"))["models"][key]["reasoning_max_tokens"] == 20000


def test_non_integer_reasoning_is_rejected(tmp_path):
    r = _run(tmp_path, "RUN_SEC=1\nREASONING_MAX_TOKENS_SEC=abc\n", "--dry-run")
    assert r.returncode != 0
    assert "整数でない" in r.stderr + r.stdout
