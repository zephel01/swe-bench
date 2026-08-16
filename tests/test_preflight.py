"""preflight (設定照合) の回帰テスト.

2026-08 に実際に起きた2つの事故を再現ケースとして固定する。

  事故1: seed / top_p / top_k / min_p が payload に載っておらず、
         llama-server 既定 (seed=-1 = 毎回ランダム) が効いていた
  事故2: temperature を config に書いていなかったため、
         llmbench のクラス既定 0.2 が黙って使われていた (モデル推奨は 1.0)

しきい値は実測分布 (1,860タスク分の llm_output.txt) から決めているので、
ここの数値を動かすときは根拠データも一緒に更新すること。
"""

from __future__ import annotations

import json

import pytest

from llmbench.preflight import (
    PreflightReport,
    check_degeneration,
    check_effective,
    check_recommended,
    degeneration_metrics,
    normalize_generation_config,
    resolve_repo_id,
    scan_artifacts,
)


def _levels(report, check=None, key=None):
    return [
        f.level for f in report.findings
        if (check is None or f.check == check) and (key is None or f.key == key)
    ]


# ------------------------------------------------------------ A: 公式推奨


def test_recommended_matches():
    r = PreflightReport(model="m")
    check_recommended(r, {"temperature": 1.0, "top_p": 0.95}, {"temperature": 1.0, "top_p": 0.95})
    assert set(_levels(r, "recommended")) == {"OK"}
    assert r.exit_code() == 0


def test_recommended_temperature_mismatch_is_fail():
    """事故2の再現: 推奨 1.0 に対して 0.2 を使っている."""
    r = PreflightReport(model="m")
    check_recommended(r, {"temperature": 0.2}, {"temperature": 1.0, "top_p": 0.95})
    assert "FAIL" in _levels(r, "recommended", "temperature")
    assert r.exit_code() == 1


def test_recommended_non_strict_key_is_warn_only():
    r = PreflightReport(model="m")
    check_recommended(r, {"temperature": 1.0, "top_p": 0.5}, {"temperature": 1.0, "top_p": 0.95})
    assert _levels(r, "recommended", "top_p") == ["WARN"]
    assert r.exit_code() == 0
    assert r.exit_code(strict=True) == 1


def test_recommended_missing_table_warns():
    r = PreflightReport(model="m")
    check_recommended(r, {"temperature": 1.0}, {})
    assert "WARN" in _levels(r, "recommended")


def test_normalize_generation_config():
    assert normalize_generation_config(
        {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "unrelated": 1}
    ) == {"temperature": 1.0, "top_p": 0.95, "top_k": 20}


def test_normalize_generation_config_greedy():
    """do_sample: false は greedy 推奨 = temperature 0."""
    assert normalize_generation_config({"do_sample": False, "temperature": 0.7}) == {
        "temperature": 0.0
    }


def test_resolve_repo_id_prefers_explicit():
    cfg = {"hf_repo": "Qwen/Qwen3.8-27B", "model_path": "/m/x.gguf"}
    assert resolve_repo_id("n", cfg, {"hf_repo_map": {"/m/": "other/repo"}}) == "Qwen/Qwen3.8-27B"


def test_resolve_repo_id_longest_prefix_wins():
    cfg = {"model_path": "/mnt/data/models/Qwen3.8-27B-GGUF/x.gguf"}
    run = {"hf_repo_map": {
        "/mnt/data/models/": "self/made",
        "/mnt/data/models/Qwen3.8-27B-GGUF/": "unsloth/Qwen3.8-27B-GGUF",
    }}
    assert resolve_repo_id("n", cfg, run) == "unsloth/Qwen3.8-27B-GGUF"


def test_resolve_repo_id_never_guesses():
    """パス名からの推測はしない (誤った推奨値を当てるほうが害が大きい)."""
    assert resolve_repo_id("n", {"model_path": "/m/Qwen3.8-27B-Q4_K_M.gguf"}, {}) is None


# ------------------------------------------------------------ B: 三点照合


def test_effective_detects_unsent_sampling_keys():
    """事故1の再現: config に書いたのに payload に載っていない."""
    r = PreflightReport(model="m")
    check_effective(
        r,
        cfg_raw={"temperature": 1.0, "top_p": 0.95, "seed": 42},
        payload={"temperature": 1.0, "max_tokens": 4096},  # top_p / seed が落ちている
        server_defaults={"top_p": 0.9, "seed": -1},
    )
    assert "WARN" in _levels(r, "effective", "top_p")
    assert "WARN" in _levels(r, "effective", "seed")


def test_effective_detects_silent_class_default():
    """事故2の再現: config に temperature が無く、既定 0.2 が黙って使われる."""
    r = PreflightReport(model="m")
    check_effective(
        r,
        cfg_raw={"top_p": 0.95},
        payload={"temperature": 0.2, "top_p": 0.95, "max_tokens": 4096},
        class_defaults={"temperature": 0.2},
    )
    warns = [f for f in r.findings if f.key == "temperature" and f.level == "WARN"]
    assert warns, "config 未指定のクラス既定は警告されるべき"
    assert "モデルの推奨値ではありません" in warns[0].message


def test_effective_seed_none_warns_reproducibility():
    r = PreflightReport(model="m")
    check_effective(r, cfg_raw={}, payload={"temperature": 1.0}, server_defaults={})
    seed_warn = [f for f in r.findings if f.key == "seed" and f.level == "WARN"]
    assert any("再現" in f.message for f in seed_warn)


def test_effective_max_tokens_over_ctx_is_fail():
    """実測: ctx 32768 のとき max_tokens 49152 は効かず ~32,230 で止まっていた."""
    r = PreflightReport(model="m")
    check_effective(r, cfg_raw={"max_tokens": 49152},
                    payload={"temperature": 1.0, "max_tokens": 49152},
                    n_ctx=32768)
    assert "FAIL" in _levels(r, "effective", "max_tokens")


def test_effective_max_tokens_within_ctx_is_ok():
    r = PreflightReport(model="m")
    check_effective(r, cfg_raw={"max_tokens": 49152},
                    payload={"temperature": 1.0, "max_tokens": 49152},
                    n_ctx=65536)
    assert "FAIL" not in _levels(r, "effective", "max_tokens")


def test_effective_launch_mismatch_is_info_only():
    """起動引数と payload の不一致は情報提供のみ (payload が優先される)."""
    r = PreflightReport(model="m")
    check_effective(r, cfg_raw={"temperature": 1.0},
                    payload={"temperature": 1.0, "max_tokens": 100},
                    launch={"temp": "0.2"})
    infos = [f for f in r.findings if f.key == "temperature" and f.level == "INFO"]
    assert infos and "優先" in infos[0].message


# ------------------------------------------------------------ C: 縮退指数


def test_degeneration_clean_code_is_not_flagged():
    """正常なコードは同じ短い行を何度も含む。これを縮退と誤検出してはいけない."""
    text = "\n".join(["def f(x):", "    return None"] * 25)
    m = degeneration_metrics(text)
    assert m["max_line_repeat"] == 25          # 参考値としては大きい
    assert m["max_long_line_repeat"] == 0      # 判定用は 40字未満を数えない
    assert m["max_char_run"] == 0


def test_degeneration_detects_repeated_prose():
    """実測: UD-Q4_K_XL / t095 は同じ55字の散文を204回繰り返して上限に達した."""
    line = 'Now, if name = "HIRAGANA LETTER A" first HIRAGANA. Good.'
    m = degeneration_metrics("\n".join([line] * 204))
    assert m["max_long_line_repeat"] == 204
    assert m["repeated_line"].startswith("Now, if name")


def test_degeneration_detects_char_run():
    """実測: Q6_K / t053 は '0' を7,930文字続けて出力を終えた."""
    m = degeneration_metrics('If href contains "javascript&#' + "0" * 7930)
    assert m["max_char_run"] == 7930
    assert m["longest_line"] >= 7930


def test_degeneration_empty_text():
    m = degeneration_metrics("")
    assert m["max_char_run"] == 0 and m["longest_line"] == 0


def test_scan_and_check_flags_worst_task(tmp_path):
    art = tmp_path / "run_artifacts"
    (art / "t001").mkdir(parents=True)
    (art / "t001" / "llm_output.txt").write_text("def f():\n    return 1\n", encoding="utf-8")
    (art / "t002").mkdir(parents=True)
    (art / "t002" / "llm_output.txt").write_text("x" * 9000, encoding="utf-8")

    scan = scan_artifacts(art)
    assert scan["worst"]["max_char_run"]["task"] == "t002"
    assert scan["worst"]["max_char_run"]["level"] == "FAIL"

    r = PreflightReport(model="m")
    check_degeneration(r, scan)
    assert r.exit_code() == 1


def test_scan_counts_truncation_from_results(tmp_path):
    art = tmp_path / "run_artifacts"
    (art / "t001").mkdir(parents=True)
    (art / "t001" / "llm_output.txt").write_text("ok\n", encoding="utf-8")
    res = tmp_path / "run_results.json"
    res.write_text(json.dumps({"results": [
        {"task_id": "t001", "truncated": True},
        {"task_id": "t002", "truncated": False},
    ]}), encoding="utf-8")

    scan = scan_artifacts(art, results_json=res)
    assert scan["truncation"]["n_truncated"] == 1
    assert scan["truncation"]["rate"] == 0.5
    assert scan["truncation"]["level"] == "FAIL"


def test_scan_falls_back_to_completion_tokens(tmp_path):
    """旧ハーネスの results.json には truncated が無い。completion_tokens で推定する."""
    art = tmp_path / "run_artifacts"
    (art / "t001").mkdir(parents=True)
    (art / "t001" / "llm_output.txt").write_text("ok\n", encoding="utf-8")
    res = tmp_path / "run_results.json"
    res.write_text(json.dumps({"results": [
        {"task_id": "t001", "completion_tokens": 24576, "max_tokens": 24576},
        {"task_id": "t002", "completion_tokens": 1200, "max_tokens": 24576},
    ]}), encoding="utf-8")
    scan = scan_artifacts(art, results_json=res)
    assert scan["truncation"]["tasks"] == ["t001"]


def test_scan_empty_dir_is_safe(tmp_path):
    scan = scan_artifacts(tmp_path)
    assert scan["tasks"] == {}
    r = PreflightReport()
    check_degeneration(r, scan)
    assert r.exit_code() == 0


# ------------------------------------------------------------ レポート


def test_report_worst_and_render():
    r = PreflightReport(model="m")
    r.add("OK", "effective", "top_p", "ok")
    r.add("WARN", "effective", "seed", "seed 未指定")
    assert r.worst == "WARN"
    out = r.render()
    assert "preflight: m" in out and "seed 未指定" in out and "判定: WARN" in out


def test_report_json_roundtrip():
    r = PreflightReport(model="m")
    r.add("FAIL", "recommended", "temperature", "ズレています", recommended=1.0, effective=0.2)
    data = json.loads(json.dumps(r.to_dict(), ensure_ascii=False))
    assert data["worst"] == "FAIL"
    assert data["findings"][0]["detail"]["recommended"] == 1.0


@pytest.mark.parametrize("level,strict,expected", [
    ("OK", False, 0), ("INFO", False, 0), ("WARN", False, 0),
    ("WARN", True, 1), ("FAIL", False, 1), ("FAIL", True, 1),
])
def test_exit_codes(level, strict, expected):
    r = PreflightReport(model="m")
    r.add(level, "effective", "k", "msg")
    assert r.exit_code(strict=strict) == expected
