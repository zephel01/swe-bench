"""実行環境メタデータ (llmbench/env.py) の収集とレポート出力の検証.

要件:
  - 収集は best-effort で **絶対に例外を出さない** (ベンチ本体を止めない)
  - api_key などの秘匿値を results.json に混入させない
  - ローカル推論では量子化・GPUオフロード率・n_ctx まで残す
    (tok/s はこれらで数倍変わるため、スペック表記だけでは比較できない)
  - リモート推論ではホストのスペックが速度に無関係である旨を明示する
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from llmbench import env as envinfo
from llmbench.report import _env_section

OLLAMA_PS = {
    "models": [{
        "name": "qwen2.5-coder:32b",
        "model": "qwen2.5-coder:32b",
        "size": 21_000_000_000,
        "size_vram": 21_000_000_000,
        "context_length": 32768,
        "details": {
            "family": "qwen2",
            "parameter_size": "32.8B",
            "quantization_level": "Q4_K_M",
        },
    }]
}
LLAMACPP_PROPS = {
    "default_generation_settings": {"n_ctx": 32768},
    "total_slots": 4,
    "model_path": "/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
    "build_info": "b4321-abc",
}
_ROUTES = {
    "/api/ps": OLLAMA_PS,
    "/api/version": {"version": "0.6.2"},
    "/props": LLAMACPP_PROPS,
}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # テスト出力を汚さない
        pass

    def do_GET(self):  # noqa: N802
        body = _ROUTES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        b = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


@pytest.fixture(scope="module")
def server_url():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


# ────────────────────────── 収集の頑健性・安全性 ──────────────────────────

CFGS = [
    {"type": "openai", "base_url": "http://localhost:8085/v1", "model": "auto",
     "api_key": "sk-TOPSECRET"},
    {"type": "openai", "base_url": "https://api.example.com/v1",
     "model": "some-model", "api_key": "sk-TOPSECRET"},
    {"type": "ollama", "base_url": "http://localhost:11434", "model": "q:32b"},
    {"type": "cli", "preset": "claude"},
    {"type": "mock", "mode": "gold"},
    {},                     # 型未指定でも落ちない
    {"type": "unknown-x"},  # 未知の型でも落ちない
]


@pytest.mark.parametrize("cfg", CFGS)
def test_collect_never_raises_and_is_json_serializable(cfg):
    env = envinfo.collect(cfg)
    json.dumps(env)  # results.json に埋められること
    assert "execution" in env
    envinfo.format_summary(env)  # サマリ生成も落ちない


@pytest.mark.parametrize("cfg", CFGS)
def test_no_secret_leak(cfg):
    """api_key が環境情報に混入しないこと (results.json は共有されうる)."""
    assert "TOPSECRET" not in json.dumps(envinfo.collect(cfg), ensure_ascii=False)


def test_collect_host_has_minimum_keys():
    host = envinfo.collect_host()
    assert host.get("os") and host.get("arch") and host.get("python")


@pytest.mark.parametrize("raw,expected", [
    ("spdisplays_metal4", "Metal 4"),
    ("spdisplays_metal3", "Metal 3"),
    ("Metal 3", "Metal 3"),
    ("unknown-value", "unknown-value"),
])
def test_macos_metal_label_is_humanized(monkeypatch, raw, expected):
    """system_profiler の内部キー名をそのままレポートに出さない."""
    payload = json.dumps({"SPDisplaysDataType": [
        {"sppci_model": "Apple M3 Max", "sppci_cores": "40",
         "spdisplays_mtlgpufamilysupport": raw}
    ]})
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: payload)
    gpus = envinfo._gpu_macos()
    assert gpus == [{"name": "Apple M3 Max", "cores": 40, "metal": expected}]


def test_execution_kind_classification():
    def ex(cfg):
        return envinfo.collect(cfg)["execution"]

    assert ex({"type": "ollama", "base_url": "http://localhost:11434"}) == "local"
    assert ex({"type": "openai", "base_url": "http://127.0.0.1:8085/v1"}) == "local"
    assert ex({"type": "openai",
               "base_url": "https://api.z.ai/api/coding/paas/v4"}) == "remote-api"
    assert ex({"type": "cli", "preset": "claude"}) == "subscription-cli"
    assert ex({"type": "mock"}) == "mock"


# ─────────────────────── バックエンド構成のパース ───────────────────────


def test_backend_ollama_parses_offload_ratio(server_url):
    b = envinfo.collect_backend(
        {"type": "ollama", "base_url": server_url, "model": "qwen2.5-coder:32b"}
    )
    assert b["kind"] == "ollama"
    assert b["quantization"] == "Q4_K_M"
    assert b["parameter_size"] == "32.8B"
    assert b["n_ctx"] == 32768
    # size_vram == size → 全層GPU
    assert b["gpu_offload_ratio"] == 1.0
    assert b["server_version"] == "ollama 0.6.2"


def test_backend_llamacpp_parses_props_and_quant(server_url):
    b = envinfo.collect_backend(
        {"type": "openai", "base_url": f"{server_url}/v1", "model": "auto"},
        served_model="Qwen3-Coder-30B",
    )
    assert b["kind"] == "llama.cpp"
    assert b["n_ctx"] == 32768
    assert b["parallel_slots"] == 4
    # ggufファイル名から量子化を拾う
    assert b["quantization"] == "Q4_K_M"
    assert b["model"] == "Qwen3-Coder-30B"


def test_backend_remote_does_not_probe_local_endpoints():
    """リモートAPIには /props を投げない (無駄な通信をしない)."""
    b = envinfo.collect_backend(
        {"type": "openai", "base_url": "https://api.example.invalid/v1",
         "model": "m"}
    )
    assert b["kind"] == "openai-compat-api"
    assert "n_ctx" not in b


# ────────────────────────── レポート出力 ──────────────────────────


def test_report_section_local_shows_backend_config(server_url):
    env = envinfo.collect(
        {"type": "ollama", "base_url": server_url, "model": "qwen2.5-coder:32b"}
    )
    md = "\n".join(_env_section(env))
    assert "## 🖥 実行環境" in md
    assert "Q4_K_M" in md
    assert "GPUオフロード率" in md
    assert "計測クライアント" not in md  # ローカルでは警告を出さない


def test_report_section_remote_warns_specs_are_client_side():
    env = envinfo.collect({"type": "cli", "preset": "claude"})
    md = "\n".join(_env_section(env))
    assert "計測クライアント" in md
    assert "同列に比較しないこと" in md


def test_report_section_empty_env_is_omitted():
    assert _env_section({}) == []


def test_partial_offload_is_flagged():
    """GPUに載りきっていない場合は警告マークを出す (tok/s が落ちる主因)."""
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "ollama", "gpu_offload_ratio": 0.62, "vram_resident_gb": 13.0}}
    md = "\n".join(_env_section(env))
    assert "⚠️ 62%" in md


# ────────────────────── results.json への埋め込み ──────────────────────


def test_save_run_embeds_environment(tmp_path):
    from llmbench.runner import RunResult, save_run

    run = RunResult(model="m", issue_lang="en")
    run.environment = envinfo.collect({"type": "mock"})
    json_path, md_path = save_run(run, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["environment"]["execution"] == "mock"
    assert "## 🖥 実行環境" in md_path.read_text(encoding="utf-8")


def test_save_run_without_environment_stays_backward_compatible(tmp_path):
    from llmbench.runner import RunResult, save_run

    json_path, md_path = save_run(RunResult(model="m", issue_lang="en"), tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "environment" not in payload
    assert "## 🖥 実行環境" not in md_path.read_text(encoding="utf-8")


def test_compare_warns_on_mixed_environments():
    from llmbench.compare import render_comparison

    def _run(model, env):
        d = {"model": model, "issue_lang": "en",
             "summary": {"resolved_rate": 0.5, "avg_quality_resolved": 50,
                         "avg_combined": 50, "runs": 1, "usability": {}},
             "results": [{"task_id": "t1", "difficulty": "easy", "title": "a",
                          "combined": 50, "tokens_per_sec": 30}]}
        if env:
            d["environment"] = env
        return d

    local = {"execution": "local", "host": {"cpu": "M3 Max", "ram_gb": 128.0},
             "backend": {"kind": "ollama", "quantization": "Q4_K_M"}}
    remote = {"execution": "remote-api", "host": {"cpu": "M3 Max"},
              "backend": {"kind": "openai-compat-api", "model": "x"}}
    md = render_comparison([_run("a", local), _run("b", remote)])
    assert "測定環境が揃っていません" in md
    # 同一環境なら比較可能と示す
    md2 = render_comparison([_run("a", local), _run("b", dict(local))])
    assert "同一環境で測定されています" in md2
    # 環境未記録 (旧results) も検出する
    md3 = render_comparison([_run("a", local), _run("b", None)])
    assert "記録されていない" in md3
