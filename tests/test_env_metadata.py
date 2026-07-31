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


# ─────────────────── マルチGPU: どのGPUに載ったか ───────────────────

# 実機 (RTX 3090 + RTX 5090, llama-server が両方に分割ロード) の nvidia-smi 出力
_GPU_QUERY = (
    "GPU-aaaa, 0, NVIDIA GeForce RTX 3090, 6129, 24576\n"
    "GPU-bbbb, 1, NVIDIA GeForce RTX 5090, 6760, 32607"
)
_APPS_SPLIT = (
    "GPU-aaaa, 3596389, /home/u/llama.cpp/build-cuda/bin/llama-server, 6106\n"
    "GPU-bbbb, 3596389, /home/u/llama.cpp/build-cuda/bin/llama-server, 6750"
)
_APPS_SINGLE = (
    "GPU-bbbb, 3596389, /home/u/llama.cpp/build-cuda/bin/llama-server, 6750"
)


def _fake_smi(monkeypatch, gpu_out, apps_out):
    def _sh(cmd, timeout=None):
        if cmd[0] != "nvidia-smi":
            return None
        joined = " ".join(cmd)
        if "--query-compute-apps" in joined:
            return apps_out
        if "--query-gpu" in joined:
            return gpu_out
        return None

    monkeypatch.setattr(envinfo, "_sh", _sh)


def test_gpu_usage_detects_tensor_split_across_gpus(monkeypatch):
    """同一PIDが複数GPUに出る = 分割ロード。「どちらか」ではなく分割として記録する."""
    _fake_smi(monkeypatch, _GPU_QUERY, _APPS_SPLIT)
    usage = envinfo.collect_gpu_usage()
    inf = usage["inference"]
    assert inf["multi_gpu"] is True
    assert inf["pid"] == 3596389
    assert inf["process"] == "llama-server"   # フルパスから実行ファイル名を抽出
    assert [g["index"] for g in inf["gpus"]] == [0, 1]
    assert [g["name"] for g in inf["gpus"]] == [
        "NVIDIA GeForce RTX 3090", "NVIDIA GeForce RTX 5090"]
    assert inf["vram_total_gb"] == 12.6        # 6.0 + 6.6
    assert "uncertain" not in inf
    # 搭載GPU全体の使用量も残す
    assert [g["vram_total_gb"] for g in usage["gpus"]] == [24.0, 31.8]


def test_gpu_usage_single_gpu_is_not_flagged_multi(monkeypatch):
    _fake_smi(monkeypatch, _GPU_QUERY, _APPS_SINGLE)
    inf = envinfo.collect_gpu_usage()["inference"]
    assert inf["multi_gpu"] is False
    assert [g["index"] for g in inf["gpus"]] == [1]


def test_gpu_usage_unknown_process_is_marked_uncertain(monkeypatch):
    _fake_smi(monkeypatch, _GPU_QUERY, "GPU-bbbb, 42, /usr/bin/blender, 6750")
    inf = envinfo.collect_gpu_usage()["inference"]
    assert inf["uncertain"] is True


def test_gpu_usage_without_nvidia_returns_empty(monkeypatch):
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: None)
    assert envinfo.collect_gpu_usage() == {}


def test_gpu_usage_only_collected_for_local_execution(monkeypatch):
    """リモートAPIではローカルGPUを覗いても意味がないので収集しない."""
    _fake_smi(monkeypatch, _GPU_QUERY, _APPS_SPLIT)
    remote = envinfo.collect({"type": "openai",
                              "base_url": "https://api.example.invalid/v1"})
    assert "gpu_usage" not in remote["backend"]


def test_summary_prefers_actual_inference_gpus(monkeypatch):
    """マルチGPU機で搭載1枚目だけを出すと誤解を生むため、実使用GPUを出す."""
    env = {"execution": "local", "host": {"gpu": [
        {"name": "NVIDIA GeForce RTX 3090", "vram_gb": 24.0}]},
        "backend": {"gpu_usage": {"inference": {
            "multi_gpu": True, "vram_total_gb": 12.6, "gpus": [
                {"index": 0, "name": "RTX 3090", "vram_gb": 6.0},
                {"index": 1, "name": "RTX 5090", "vram_gb": 6.6}]}}}}
    s = envinfo.format_summary(env)
    assert "RTX 3090 6.0GB + RTX 5090 6.6GB" in s
    assert "計12.6GB を分割" in s


# ────────── 計算バックエンド (CUDA / ROCm / Vulkan) の判別 ──────────
#
# llama.cpp の /props は build_info しか返さず、どのバックエンドでビルドされたかは
# APIから取れない。tok/s を最も左右する要素なので、プロセスのロード済み
# ライブラリから逆算する。

_MAPS = {
    "cuda": (
        "7f00-7f01 r--p /usr/lib/x86_64-linux-gnu/libcudart.so.13\n"
        "7f02-7f03 r--p /usr/lib/x86_64-linux-gnu/libcublas.so.13\n"
        "7f04-7f05 r--p /usr/lib/x86_64-linux-gnu/libc.so.6\n"
    ),
    "rocm": (
        "7f00-7f01 r--p /opt/rocm/lib/libamdhip64.so.6\n"
        "7f02-7f03 r--p /opt/rocm/lib/librocblas.so.4\n"
    ),
    "vulkan": (
        "7f00-7f01 r--p /usr/lib/x86_64-linux-gnu/libvulkan.so.1\n"
        "7f02-7f03 r--p /usr/lib/x86_64-linux-gnu/libggml-vulkan.so\n"
    ),
    "cpu": "7f00-7f01 r--p /usr/lib/x86_64-linux-gnu/libc.so.6\n",
}


def _fake_proc(monkeypatch, maps, exe):
    monkeypatch.setattr(envinfo, "_proc_maps", lambda pid: maps)
    monkeypatch.setattr(envinfo, "_proc_exe", lambda pid: exe)


@pytest.mark.parametrize("key,expected", [
    ("cuda", "CUDA"), ("rocm", "ROCm"), ("vulkan", "Vulkan"), ("cpu", "CPU"),
])
def test_detect_runtime_from_loaded_libraries(monkeypatch, key, expected):
    _fake_proc(monkeypatch, _MAPS[key], "/home/u/llama.cpp/build/bin/llama-server")
    assert envinfo.detect_runtime(3596389)["compute"] == expected


def test_cuda_build_loading_vulkan_is_not_misdetected(monkeypatch):
    """CUDAビルドが libvulkan を間接ロードしていても Vulkan と誤判定しない."""
    _fake_proc(monkeypatch, _MAPS["cuda"] + _MAPS["vulkan"], None)
    rt = envinfo.detect_runtime(1)
    assert rt["compute"] == "CUDA"
    assert "Vulkan" in rt["also_loaded"]


def test_binary_path_is_used_as_hint(monkeypatch):
    """ライブラリを読めなくても build-rocm 等のパスから判る."""
    _fake_proc(monkeypatch, None, "/home/u/llama.cpp/build-rocm/bin/llama-server")
    rt = envinfo.detect_runtime(1)
    assert rt["compute"] == "ROCm"
    assert rt["binary_hint"] == "ROCm"
    assert rt["binary"].endswith("build-rocm/bin/llama-server")


def test_detect_runtime_without_pid_is_empty():
    assert envinfo.detect_runtime(None) == {}


def test_find_server_pid_prefers_matching_port(monkeypatch):
    """同じポートでビルドを差し替える運用のため、ポート一致を最優先する."""
    monkeypatch.setattr(envinfo, "_proc_cmdlines", lambda: [
        (100, "/usr/bin/gnome-shell"),
        (200, "/home/u/llama.cpp/build-cuda/bin/llama-server --port 9000"),
        (300, "/home/u/llama.cpp/build-rocm/bin/llama-server --port 8085"),
    ])
    assert envinfo.find_server_pid(8085) == 300
    assert envinfo.find_server_pid(None) == 200   # 指定なしなら先頭
    monkeypatch.setattr(envinfo, "_proc_cmdlines", lambda: [(1, "/usr/bin/bash")])
    assert envinfo.find_server_pid(8085) is None


def test_config_runtime_overrides_detection(monkeypatch):
    """config の runtime: を正とし、検出値と食い違ったら mismatch を立てる."""
    _fake_proc(monkeypatch, _MAPS["cuda"], None)
    monkeypatch.setattr(envinfo, "find_server_pid", lambda port: 1)
    monkeypatch.setattr(envinfo, "collect_gpu_usage", lambda: {})
    cfg = {"type": "openai", "base_url": "http://localhost:8085/v1",
           "runtime": "llama.cpp/Vulkan"}
    rt = envinfo.collect(cfg)["backend"]["runtime"]
    assert rt["compute"] == "llama.cpp/Vulkan"
    assert rt["source"] == "config"
    assert rt["detected"] == "CUDA" and rt["mismatch"] is True


def test_detection_used_when_config_has_no_runtime(monkeypatch):
    _fake_proc(monkeypatch, _MAPS["rocm"], None)
    monkeypatch.setattr(envinfo, "find_server_pid", lambda port: 1)
    monkeypatch.setattr(envinfo, "collect_gpu_usage", lambda: {})
    rt = envinfo.collect({"type": "openai",
                          "base_url": "http://localhost:8085/v1"})["backend"]["runtime"]
    assert rt["compute"] == "ROCm" and rt["source"] == "detected"


def test_runtime_not_probed_for_remote(monkeypatch):
    monkeypatch.setattr(envinfo, "find_server_pid",
                        lambda port: pytest.fail("リモートでプロセス走査しない"))
    env = envinfo.collect({"type": "openai",
                           "base_url": "https://api.example.invalid/v1"})
    assert "runtime" not in env["backend"]


def test_amd_gpu_is_enumerated(monkeypatch):
    """ROCm/Vulkan で Radeon を使う場合、nvidia-smi だけではGPU欄が空になる."""
    def _sh(cmd, timeout=None):
        if cmd[0] == "rocm-smi" and "--showproductname" in cmd:
            return ("device,Card Series,Card Model,Card Vendor\n"
                    "card0,Radeon 8060S Graphics,0x150e,AMD")
        return None

    monkeypatch.setattr(envinfo, "_sh", _sh)
    assert envinfo._gpu_amd() == [
        {"name": "Radeon 8060S Graphics", "vendor": "amd"}]


def test_amd_gpu_falls_back_to_lspci(monkeypatch):
    def _sh(cmd, timeout=None):
        if cmd[0] == "lspci":
            return ('c5:00.0 "VGA compatible controller" "AMD/ATI" '
                    '"Radeon 8060S" -r10 "AMD" "Device 150e"')
        return None

    monkeypatch.setattr(envinfo, "_sh", _sh)
    gpus = envinfo._gpu_amd()
    assert gpus and gpus[0]["vendor"] == "amd" and "Radeon" in gpus[0]["name"]


def test_report_shows_compute_backend_and_mismatch():
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "llama.cpp", "runtime": {
            "compute": "llama.cpp/Vulkan", "source": "config",
            "detected": "CUDA", "mismatch": True,
            "binary": "/home/u/llama.cpp/build-cuda/bin/llama-server"}}}
    md = "\n".join(_env_section(env))
    assert "計算バックエンド" in md
    assert "llama.cpp/Vulkan (config指定)" in md
    assert "検出値は **CUDA** で不一致" in md
    assert "build-cuda/bin/llama-server" in md


def test_report_shows_detected_backend_with_evidence():
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "llama.cpp", "runtime": {
            "compute": "ROCm", "source": "detected",
            "evidence": ["libamdhip64.so.6", "librocblas.so.4"]}}}
    md = "\n".join(_env_section(env))
    assert "ROCm (自動検出) — libamdhip64.so.6, librocblas.so.4" in md
    assert "不一致" not in md


# ────────── 起動引数からの推論構成 (--device / -ngl / …) ──────────
#
# llama.cpp の /props は GPUオフロード量 (-ngl) も使用デバイス (--device) も
# 返さない。起動引数には全部書いてあるので、CUDA/ROCm/Vulkan 共通でここを読む。

# 実機の llama-server 起動引数 (ROCm ビルド)
_ROCM_ARGV = [
    "/home/u/llama.cpp/build-rocm/bin/llama-server",
    "-m", "/mnt/data/models/Qwythos-9B-v2-GGUF/Qwythos-9B-v2-MTP-Q8_0.gguf",
    "--port", "8085", "--device", "ROCm0", "--spec-type", "draft-mtp",
    "-ngl", "0", "--ctx-size", "32768", "--threads", "16", "--mlock",
]
_HOST_GPUS = [
    {"name": "NVIDIA GeForce RTX 3090", "vendor": "nvidia"},
    {"name": "NVIDIA GeForce RTX 5090", "vendor": "nvidia"},
    {"name": "AMD Radeon 8060S Graphics", "vendor": "amd"},
]


def test_parse_server_args_reads_real_launch_line():
    a = envinfo.parse_server_args(_ROCM_ARGV)
    assert a["device"] == "ROCm0"
    assert a["n_gpu_layers"] == 0        # GPUに1層も載せていない
    assert a["n_ctx"] == 32768
    assert a["threads"] == 16
    assert a["spec_type"] == "draft-mtp"
    assert a["mlock"] is True


def test_parse_server_args_short_and_long_forms():
    a = envinfo.parse_server_args(
        ["llama-server", "-c", "4096", "--n-gpu-layers", "99",
         "-ts", "0,1", "-mg", "1", "-fa"])
    assert a["n_ctx"] == 4096 and a["n_gpu_layers"] == 99
    assert a["tensor_split"] == "0,1" and a["main_gpu"] == 1
    assert a["flash_attn"] is True


def test_launch_command_redacts_secrets():
    """results.json は共有されうるので、起動引数の秘匿値は必ず伏せる."""
    cmd = envinfo._redact_argv(
        ["llama-server", "--api-key", "sk-TOPSECRET", "--port", "8085",
         "--api-key-file=/etc/TOPSECRET"])
    assert "TOPSECRET" not in cmd
    assert "--api-key ***" in cmd and "--port 8085" in cmd


# ── 実機 (NucBox EVO-X2) の `llama-server --list-devices` 出力そのまま ──
#
# ★ CUDA の既定順は FASTEST_FIRST なので CUDA0 が RTX 5090。
#   nvidia-smi は PCI バス順で GPU0 が RTX 3090 → 添字で引くと逆になる。
# ★ 同じ GPU でもビルドが違えば ID も番号も違う:
#     RTX 3090       → CUDA1 / Vulkan0
#     RTX 5090       → CUDA0 / Vulkan1
#     Radeon 8060S   → ROCm0 / Vulkan2 (名前の表記まで違う)
_LIST_DEVICES_CUDA = (
    "Available devices:\n"
    "  CUDA0: NVIDIA GeForce RTX 5090 (32149 MiB, 31136 MiB free)\n"
    "  CUDA1: NVIDIA GeForce RTX 3090 (24123 MiB, 16522 MiB free)\n"
)
_LIST_DEVICES_ROCM = (
    "Available devices:\n"
    "  ROCm0: AMD Radeon 8060S Graphics (98304 MiB, 15342 MiB free)\n"
)
_LIST_DEVICES_VULKAN = (
    "Available devices:\n"
    "  Vulkan0: NVIDIA GeForce RTX 3090 (24822 MiB, 17008 MiB free)\n"
    "  Vulkan1: NVIDIA GeForce RTX 5090 (32607 MiB, 31641 MiB free)\n"
    "  Vulkan2: Radeon 8060S Graphics (RADV GFX1151) (114164 MiB, 113573 MiB free)\n"
)


def test_list_devices_parses_nested_parens_in_name(monkeypatch):
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_VULKAN)
    devs = envinfo.list_devices("/x/llama-server")
    assert [d["id"] for d in devs] == ["Vulkan0", "Vulkan1", "Vulkan2"]
    # 見出し行 "Available devices:" はデバイスとして拾わない
    assert len(devs) == 3
    # 名前中の括弧を巻き込まず、行末のメモリ括弧だけを切り出す
    assert devs[2]["name"] == "Radeon 8060S Graphics (RADV GFX1151)"
    assert devs[2]["vram_total_gb"] == 111.5
    assert devs[2]["vram_free_gb"] == 110.9


def test_same_gpu_has_different_id_per_build(monkeypatch):
    """RTX 3090 は CUDA1 だが Vulkan0。ビルドを跨いで番号を流用できない."""
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_CUDA)
    cuda = envinfo.resolve_device("CUDA1", [], binary="/x")["device_name"]
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_VULKAN)
    vulkan = envinfo.resolve_device("Vulkan0", [], binary="/x")["device_name"]
    assert cuda == vulkan == "NVIDIA GeForce RTX 3090"


@pytest.mark.parametrize("dev,expected", [
    ("CUDA0", "NVIDIA GeForce RTX 5090"),
    ("CUDA1", "NVIDIA GeForce RTX 3090"),
])
def test_cuda_device_order_is_not_nvidia_smi_order(monkeypatch, dev, expected):
    """CUDA0 = 5090。nvidia-smi の GPU0(=3090) と取り違えない (実機で踏んだ回帰).

    --list-devices が正。ベンダ別一覧の添字で引くと逆になる。
    """
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_CUDA)
    r = envinfo.resolve_device(dev, _HOST_GPUS, binary="/x/llama-server")
    assert r["device_name"] == expected
    assert r["device_name_source"] == "--list-devices"
    assert "device_name_uncertain" not in r


def test_resolve_device_handles_multiple_ids(monkeypatch):
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_CUDA)
    r = envinfo.resolve_device("CUDA0,CUDA1", _HOST_GPUS,
                               binary="/x/llama-server")
    assert r["device_name"] == "NVIDIA GeForce RTX 5090 + NVIDIA GeForce RTX 3090"
    assert [d["id"] for d in r["devices"]] == ["CUDA0", "CUDA1"]


def test_rocm_and_vulkan_resolve_through_the_same_path(monkeypatch):
    """ROCm / Vulkan も --list-devices で解決する (バックエンド分岐なし)."""
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_VULKAN)
    r = envinfo.resolve_device("Vulkan2", [], binary="/x/llama-server")
    assert r["device_name"] == "Radeon 8060S Graphics (RADV GFX1151)"
    assert r["device_name_source"] == "--list-devices"
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: _LIST_DEVICES_ROCM)
    r = envinfo.resolve_device("ROCm0", [], binary="/x/llama-server")
    # 同じ物理GPUでもビルドによって表記が違う (ROCm は "AMD " が付く)
    assert r["device_name"] == "AMD Radeon 8060S Graphics"


def test_fallback_guess_is_marked_uncertain():
    """--list-devices が取れないときの添字推定は必ず uncertain を立てる."""
    r = envinfo.resolve_device("CUDA0", _HOST_GPUS)   # binary なし
    assert r["device_name_uncertain"] is True


@pytest.mark.parametrize("dev,expected", [
    ("ROCm0", "AMD Radeon 8060S Graphics"),
    ("CUDA0", "NVIDIA GeForce RTX 3090"),
    ("CUDA1", "NVIDIA GeForce RTX 5090"),
])
def test_resolve_device_falls_back_to_vendor_index(dev, expected):
    assert envinfo.resolve_device(dev, _HOST_GPUS)["device_name"] == expected


def test_resolve_device_vulkan_uses_vulkaninfo(monkeypatch):
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: (
        "GPU0:\n\tdeviceName = NVIDIA GeForce RTX 3090\n"
        "GPU1:\n\tdeviceName = NVIDIA GeForce RTX 5090\n"
        "GPU2:\n\tdeviceName = AMD Radeon 8060S Graphics (RADV GFX1151)\n"))
    r = envinfo.resolve_device("Vulkan2", _HOST_GPUS)
    assert r["device_name"] == "AMD Radeon 8060S Graphics (RADV GFX1151)"
    assert "device_name_uncertain" not in r


def test_resolve_device_vulkan_falls_back_with_uncertainty(monkeypatch):
    monkeypatch.setattr(envinfo, "_sh", lambda *a, **k: None)  # vulkaninfo無し
    r = envinfo.resolve_device("Vulkan2", _HOST_GPUS)
    assert r["device_name"] == "AMD Radeon 8060S Graphics"
    assert r["device_name_uncertain"] is True


def test_resolve_device_unparsable_is_kept_as_is():
    assert envinfo.resolve_device("none", [])["device"] == "none"
    assert envinfo.resolve_device("", []) == {}


def _fake_local_server(monkeypatch, argv, maps, env_vars=None):
    monkeypatch.setattr(envinfo, "find_server_pid", lambda port: 4242)
    monkeypatch.setattr(envinfo, "_proc_argv", lambda pid: argv)
    monkeypatch.setattr(envinfo, "_proc_maps", lambda pid: maps)
    monkeypatch.setattr(envinfo, "_proc_exe", lambda pid: argv[0])
    monkeypatch.setattr(envinfo, "_proc_visible_env", lambda pid: env_vars or {})
    monkeypatch.setattr(envinfo, "collect_host", lambda: {"gpu": _HOST_GPUS})
    monkeypatch.setattr(envinfo, "collect_backend",
                        lambda cfg, sm=None: {"kind": "llama.cpp"})


def test_collect_records_device_and_ngl(monkeypatch):
    _fake_local_server(monkeypatch, _ROCM_ARGV, _MAPS["rocm"],
                       {"HIP_VISIBLE_DEVICES": "0"})
    monkeypatch.setattr(envinfo, "collect_gpu_usage", lambda: {})
    launch = envinfo.collect({"type": "openai",
                              "base_url": "http://localhost:8085/v1"}
                             )["backend"]["launch"]
    assert launch["device"] == "ROCm0"
    assert launch["device_name"] == "AMD Radeon 8060S Graphics"
    assert launch["n_gpu_layers"] == 0
    assert launch["visible_devices_env"] == {"HIP_VISIBLE_DEVICES": "0"}
    assert "llama-server" in launch["command"]


def test_nvidia_attribution_suppressed_for_non_cuda_runtime(monkeypatch):
    """Vulkanビルドが nvidia-smi に数十MiBで顔を出しても推論GPUと誤認しない.

    実機で「Radeon で動いているのに RTX 3090 0.0GB」と出た回帰の再発防止。
    """
    _fake_local_server(monkeypatch, ["llama-server", "--device", "Vulkan2"],
                       _MAPS["vulkan"])
    monkeypatch.setattr(envinfo, "collect_gpu_usage", lambda: {
        "inference": {"pid": 1, "process": "llama-server", "multi_gpu": False,
                      "vram_total_gb": 0.0,
                      "gpus": [{"index": 0, "name": "NVIDIA GeForce RTX 3090",
                                "vram_gb": 0.0}]},
        "gpus": [{"index": 0, "name": "NVIDIA GeForce RTX 3090"}]})
    backend = envinfo.collect({"type": "openai",
                               "base_url": "http://localhost:8085/v1"})["backend"]
    assert "inference" not in backend["gpu_usage"]
    assert "Vulkan" in backend["gpu_usage"]["note"]
    # 代わりに起動引数由来のデバイスが残る
    assert backend["launch"]["device"] == "Vulkan2"


def test_context_only_shard_is_not_counted_as_split(monkeypatch):
    """--device CUDA0 でも未選択GPUに数百MiBのコンテキストが載る.

    実機: 5090 に 7650MiB / 3090 に 256MiB。これを「2枚に分割ロード」と
    報告するのは誤りなので、ごく小さい取り分はコンテキストとして区別する。
    """
    def _sh(cmd, timeout=None):
        if cmd[0] != "nvidia-smi":
            return None
        j = " ".join(cmd)
        if "--query-compute-apps" in j:
            return ("GPU-aaaa, 3684862, /x/build-cuda/bin/llama-server, 256\n"
                    "GPU-bbbb, 3684862, /x/build-cuda/bin/llama-server, 7650")
        if "--query-gpu" in j:
            return ("GPU-aaaa, 0, NVIDIA GeForce RTX 3090, 280, 24576\n"
                    "GPU-bbbb, 1, NVIDIA GeForce RTX 5090, 7661, 32607")
        return None

    monkeypatch.setattr(envinfo, "_sh", _sh)
    inf = envinfo.collect_gpu_usage()["inference"]
    assert inf["multi_gpu"] is False          # 分割ロードではない
    assert inf["gpus"][0]["context_only"] is True   # 3090 = 0.2GB
    assert "context_only" not in inf["gpus"][1]     # 5090 = 7.5GB


def test_cuda_runtime_keeps_nvidia_attribution(monkeypatch):
    _fake_local_server(monkeypatch, ["llama-server", "-ngl", "99"],
                       _MAPS["cuda"])
    monkeypatch.setattr(envinfo, "collect_gpu_usage", lambda: {
        "inference": {"pid": 1, "multi_gpu": False, "vram_total_gb": 6.6,
                      "gpus": [{"index": 1, "name": "RTX 5090",
                                "vram_gb": 6.6}]}})
    usage = envinfo.collect({"type": "openai",
                             "base_url": "http://localhost:8085/v1"}
                            )["backend"]["gpu_usage"]
    assert usage["inference"]["gpus"][0]["name"] == "RTX 5090"


def test_summary_shows_device_and_flags_ngl_zero():
    env = {"execution": "local", "host": {"gpu": _HOST_GPUS}, "backend": {
        "launch": {"device": "ROCm0", "device_name": "AMD Radeon 8060S Graphics",
                   "n_gpu_layers": 0}}}
    s = envinfo.format_summary(env)
    assert "AMD Radeon 8060S Graphics" in s
    assert "-ngl 0 (GPU未使用)" in s


def test_report_flags_ngl_zero_as_cpu_execution():
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "llama.cpp",
        "runtime": {"compute": "ROCm", "source": "detected"},
        "launch": {"device": "ROCm0", "device_name": "AMD Radeon 8060S Graphics",
                   "n_gpu_layers": 0, "threads": 16, "n_ctx": 32768,
                   "command": "llama-server --device ROCm0 -ngl 0"}}}
    md = "\n".join(_env_section(env))
    assert "使用デバイス" in md and "ROCm0 — AMD Radeon 8060S Graphics" in md
    assert "GPUに1層も載せていない" in md
    assert "実質CPU実行" in md
    assert "起動コマンド" in md


def test_report_ngl_positive_has_no_cpu_warning():
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "llama.cpp",
        "launch": {"device": "Vulkan2", "n_gpu_layers": 99}}}
    md = "\n".join(_env_section(env))
    assert "`-ngl 99`" in md
    assert "実質CPU実行" not in md


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


def test_report_shows_multi_gpu_split_and_warns():
    env = {"execution": "local", "host": {"gpu": [
        {"name": "NVIDIA GeForce RTX 3090", "vram_gb": 24.0,
         "compute_capability": "8.6", "driver": "610.43.02"},
        {"name": "NVIDIA GeForce RTX 5090", "vram_gb": 31.8,
         "compute_capability": "12.0", "driver": "610.43.02"}]},
        "backend": {"kind": "llama.cpp", "gpu_usage": {"inference": {
            "process": "llama-server", "multi_gpu": True,
            "vram_total_gb": 12.6, "gpus": [
                {"index": 0, "name": "NVIDIA GeForce RTX 3090", "vram_gb": 6.0},
                {"index": 1, "name": "NVIDIA GeForce RTX 5090",
                 "vram_gb": 6.6}]}}}}
    md = "\n".join(_env_section(env))
    assert "GPU0 NVIDIA GeForce RTX 3090 6.0GB" in md
    assert "GPU1 NVIDIA GeForce RTX 5090 6.6GB" in md
    assert "計 12.6GB を 2枚に分割ロード" in md
    assert "遅い側のカード" in md          # 単体GPUと同一視しない警告
    assert "CC 8.6" in md and "CC 12.0" in md


def test_report_single_gpu_has_no_split_warning():
    env = {"execution": "local", "host": {}, "backend": {
        "kind": "llama.cpp", "gpu_usage": {"inference": {
            "process": "llama-server", "multi_gpu": False,
            "vram_total_gb": 6.6,
            "gpus": [{"index": 1, "name": "RTX 5090", "vram_gb": 6.6}]}}}}
    md = "\n".join(_env_section(env))
    assert "GPU1 RTX 5090 6.6GB" in md
    assert "分割ロード" not in md
    assert "遅い側のカード" not in md


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


def test_summary_carries_speed_metrics(tmp_path):
    """summary だけを読む外部ツール (CodeRouter 等) から速度が見えること."""
    from llmbench.runner import RunResult, TaskResult, save_run

    run = RunResult(model="m", issue_lang="en")
    run.results = [
        TaskResult(task_id="t1", difficulty="easy", title="a",
                   tokens_per_sec=30.0, latency_sec=2.0),
        TaskResult(task_id="t2", difficulty="easy", title="b",
                   tokens_per_sec=40.0, latency_sec=4.0),
        # 速度が取れなかったタスクは分母に入れない
        TaskResult(task_id="t3", difficulty="easy", title="c"),
    ]
    payload = json.loads(
        save_run(run, tmp_path)[0].read_text(encoding="utf-8"))
    assert payload["summary"]["tokens_per_sec"] == 35.0
    assert payload["summary"]["avg_latency_ms"] == 3000


def test_summary_omits_speed_metrics_when_unavailable(tmp_path):
    from llmbench.runner import RunResult, TaskResult, save_run

    run = RunResult(model="m", issue_lang="en")
    run.results = [TaskResult(task_id="t1", difficulty="easy", title="a")]
    summary = json.loads(
        save_run(run, tmp_path)[0].read_text(encoding="utf-8"))["summary"]
    assert "tokens_per_sec" not in summary
    assert "avg_latency_ms" not in summary


def test_save_run_without_environment_stays_backward_compatible(tmp_path):
    from llmbench.runner import RunResult, save_run

    json_path, md_path = save_run(RunResult(model="m", issue_lang="en"), tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "environment" not in payload
    assert "## 🖥 実行環境" not in md_path.read_text(encoding="utf-8")


# ─────────────── compare: ハードウェア比較モード ───────────────
#
# 同一モデルを別ハードで測った場合、「環境が違うから tok/s 比較不可」は裏返し。
# モデルを固定してハードを比べているのだから tok/s が主役になる。


def _hw_run(device, compute, tps, ngl=99, n_ctx=16384, model="Ornith-9B-Q6_K"):
    return {
        "model": model, "issue_lang": "en",
        "summary": {"resolved_rate": 1.0, "avg_quality_resolved": 88.6,
                    "avg_combined": 94.3, "runs": 1, "usability": {},
                    "tokens_per_sec": tps},
        "results": [{"task_id": "t001", "difficulty": "easy", "title": "a",
                     "combined": 94.3, "tokens_per_sec": tps}],
        "environment": {
            "execution": "local",
            "host": {"cpu": "AMD RYZEN AI MAX+ 395", "ram_gb": 31.0,
                     "gpu": [{"name": "NVIDIA GeForce RTX 3090",
                              "vendor": "nvidia"}]},
            "backend": {"kind": "llama.cpp", "quantization": "Q6_K",
                        "runtime": {"compute": compute},
                        "launch": {"device_name": device, "n_gpu_layers": ngl,
                                   "n_ctx": n_ctx, "parallel": 1}},
        },
    }


# 実機の4本 (同一モデル・-ngl 99・n_ctx 16384 で条件を揃えたもの)
_HW_RUNS = [
    _hw_run("NVIDIA GeForce RTX 5090", "CUDA", 149.5),
    _hw_run("NVIDIA GeForce RTX 3090", "CUDA", 63.7),
    _hw_run("AMD Radeon 8060S Graphics", "ROCm", 26.5),
    _hw_run("Radeon 8060S Graphics (RADV GFX1151)", "Vulkan", 23.7),
]


def test_hardware_comparison_is_detected_and_ranked_by_speed():
    from llmbench.compare import render_comparison

    md = render_comparison(_HW_RUNS)
    assert "# 🆚 ハードウェア比較レポート" in md
    assert "## 🖥 ランキング（tok/s 降順）" in md
    # 「比較不可」の警告は出さない (それが今回の主目的なので)
    assert "測定環境が揃っていません" not in md
    assert "条件（量子化 / -ngl / n_ctx / 並列）が全環境で一致" in md
    # ★ Combined ランキングは出さない。全環境同点で順位が意味を持たず、
    #   速い環境が下に並んで誤解を生むため (実機のレポートで確認)
    assert "Combined平均 降順" not in md
    # tok/s 降順に並ぶ
    order = [md.index(d) for d in ("RTX 5090", "RTX 3090",
                                   "AMD Radeon 8060S Graphics",
                                   "RADV GFX1151")]
    assert order == sorted(order)
    assert "149.5" in md


def test_hardware_comparison_flags_mismatched_conditions():
    """-ngl 0 (CPU実行) を混ぜたら速度差をハード差として読ませない."""
    from llmbench.compare import render_comparison

    runs = [_HW_RUNS[0],
            _hw_run("AMD Radeon 8060S Graphics", "ROCm", 27.5, ngl=0,
                    n_ctx=32768)]
    md = render_comparison(runs)
    assert "推論条件が揃っていません" in md
    assert "-ngl" in md and "n_ctx" in md
    assert "GPU を使っていません" in md


def test_hardware_mode_labels_rows_by_device_not_model():
    """モデル名が全行同じなので、表の列はデバイス名で区別する."""
    from llmbench.compare import render_comparison

    md = render_comparison(_HW_RUNS)
    matrix = md[md.index("## タスク別 Combined マトリクス"):]
    assert "NVIDIA GeForce RTX 5090 (CUDA)" in matrix
    assert "Radeon 8060S Graphics (RADV GFX1151) (Vulkan)" in matrix


def test_duplicate_device_labels_get_numbered():
    """同じデバイス×バックエンドを複数回測ってもマトリクスの列を区別できる."""
    from llmbench.compare import render_comparison

    runs = [_HW_RUNS[0],
            _hw_run("NVIDIA GeForce RTX 5090", "CUDA", 118.2),
            _HW_RUNS[2]]
    md = render_comparison(runs)
    assert "NVIDIA GeForce RTX 5090 (CUDA) #1" in md
    assert "NVIDIA GeForce RTX 5090 (CUDA) #2" in md
    # 重複していないラベルには連番を振らない
    assert "AMD Radeon 8060S Graphics (ROCm) #" not in md


def test_empty_results_are_excluded_and_reported():
    """結果0件の results は列を作るだけなので除外し、除外した旨を明示する."""
    from llmbench.compare import render_comparison

    empty = {"model": "Ornith-9B-Q6_K", "issue_lang": "en",
             "summary": {"resolved_rate": 0.0, "avg_combined": 0.0,
                         "n_tasks": 0, "runs": 1, "usability": {}},
             "results": [], "_path": "20260731_dead_results.json"}
    md = render_comparison([*_HW_RUNS, empty])
    assert "結果0件のため除外" in md
    assert "20260731_dead_results.json" in md
    # 空の run が列やランキングに混ざらない
    assert md.count("| 0.0% |") == 0
    assert "4 環境で測定" in md


def test_model_comparison_mode_is_unchanged_when_models_differ():
    from llmbench.compare import render_comparison

    runs = [_HW_RUNS[0], _hw_run("NVIDIA GeForce RTX 5090", "CUDA", 90.0,
                                 model="other-model")]
    md = render_comparison(runs)
    assert "# 🆚 モデル比較レポート" in md
    assert "ハードウェア比較" not in md


def test_compare_uses_summary_tokens_per_sec():
    """summary に速度があればそれを使う (results[] の再集計に依存しない)."""
    from llmbench.compare import _run_tps

    assert _run_tps({"summary": {"tokens_per_sec": 42.0}, "results": []}) == 42.0
    assert _run_tps({"summary": {},
                     "results": [{"tokens_per_sec": 10.0},
                                 {"tokens_per_sec": 20.0}]}) == 15.0


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
