"""実行環境 (ハードウェア・推論バックエンド構成) のメタデータ収集.

なぜ必要か:
    results.json の ``tokens_per_sec`` は「どのマシンで、どの量子化で、
    GPUに何割載った状態で測ったか」が分からないと比較できない。同じGPUでも
    量子化・GPUオフロード率・コンテキスト長で数倍変わるため、スペック表記だけ
    では不十分で「バックエンド構成」まで残す必要がある。

方針:
    - すべて best-effort。取得できない項目は None / キー省略にし、
      **例外は絶対に外へ出さない** (環境情報の取得失敗でベンチを止めない)。
    - 追加依存なし。標準ライブラリ + すでに依存済みの requests のみ。
    - api_key など秘匿値は決して含めない。
    - クラウドAPIモデルではホストのスペックはスループットに影響しないので、
      ``execution`` で「ローカル推論ではない」ことを明示する。

出力スキーマ (results.json の "environment"):
    {
      "execution": "local" | "remote-api" | "subscription-cli" | "mock",
      "note": "…人間向けの注意書き…",
      "host": {"os", "arch", "python", "cpu", "cpu_cores", "ram_gb", "gpu": [...]},
      "backend": {"kind", "base_url", "model", "quantization", ...}
    }
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys

__all__ = [
    "EXEC_LABEL", "collect", "collect_host", "collect_backend",
    "collect_gpu_usage", "detect_runtime", "find_server_pid", "format_summary",
]

# execution の人間向けラベル (report / compare 共通)
EXEC_LABEL = {
    "local": "🖥 ローカル推論",
    "remote-api": "☁️ クラウドAPI",
    "subscription-cli": "☁️ サブスクCLI (ベンダ側で推論)",
    "mock": "🧪 モック",
    "unknown": "❔ 不明",
}

_CMD_TIMEOUT = 6.0
_HTTP_TIMEOUT = 3.0

# ローカル推論とみなすホスト名 (base_url の host 部分)
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal")


def _sh(cmd: list[str], timeout: float = _CMD_TIMEOUT) -> str | None:
    """コマンドを実行して stdout を返す. 失敗時は None (例外を出さない)."""
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _sysctl(key: str) -> str | None:
    return _sh(["sysctl", "-n", key])


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _gb(nbytes) -> float | None:
    n = _int(nbytes)
    return round(n / (1024 ** 3), 1) if n else None


def _get_json(url: str, timeout: float = _HTTP_TIMEOUT):
    """GET して JSON を返す. 失敗時 None (requests未導入でも落ちない)."""
    try:
        import requests
    except Exception:
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code >= 400:
            return None
        return resp.json()
    except Exception:
        return None


def _port_of(base_url: str) -> int | None:
    try:
        from urllib.parse import urlparse

        return urlparse(base_url).port
    except Exception:
        return None


def _is_local_url(base_url: str) -> bool:
    try:
        from urllib.parse import urlparse

        host = (urlparse(base_url).hostname or "").lower()
    except Exception:
        return False
    return host in _LOCAL_HOSTS or host.endswith(".local")


# ─────────────────────────── ホスト (ハードウェア) ───────────────────────────


def _gpu_macos() -> list[dict]:
    """system_profiler から GPU 情報を取る (Apple Silicon / 外付けGPU 両対応)."""
    raw = _sh(["system_profiler", "-json", "SPDisplaysDataType"], timeout=15.0)
    if not raw:
        return []
    try:
        items = json.loads(raw).get("SPDisplaysDataType") or []
    except Exception:
        return []
    gpus = []
    for it in items:
        g: dict = {"name": it.get("sppci_model") or it.get("_name")}
        # Apple Silicon: "sppci_cores" にGPUコア数 (例: "40")
        cores = _int(it.get("sppci_cores"))
        if cores:
            g["cores"] = cores
        # 専用VRAM (discrete GPU のみ。Apple Silicon は unified memory なので無い)
        vram = it.get("spdisplays_vram") or it.get("spdisplays_vram_shared")
        if vram:
            g["vram"] = str(vram)
        # Metal 対応世代。system_profiler は内部キー名 ("spdisplays_metal4") を
        # そのまま返すので、人が読める形 ("Metal 4") に整える。
        mtl = it.get("spdisplays_mtlgpufamilysupport")
        if mtl:
            m = re.search(r"metal[_ ]?(\d+)", str(mtl), re.I)
            g["metal"] = f"Metal {m.group(1)}" if m else str(mtl)
        gpus.append({k: v for k, v in g.items() if v})
    return gpus


def _gpu_nvidia() -> list[dict]:
    """nvidia-smi から GPU 情報を取る (NVIDIA機のみ)."""
    out = _sh([
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version,compute_cap",
        "--format=csv,noheader,nounits",
    ])
    if not out:
        return []
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        g: dict = {"name": parts[0], "vendor": "nvidia"}
        if len(parts) > 1 and _int(parts[1]):
            g["vram_gb"] = round(_int(parts[1]) / 1024, 1)  # MiB → GiB
        if len(parts) > 2 and parts[2]:
            g["driver"] = parts[2]
        if len(parts) > 3 and parts[3]:
            g["compute_capability"] = parts[3]
        gpus.append(g)
    return gpus


# 推論サーバとみなすプロセス名 (どのGPUで推論が走ったかの判定に使う)
_INFERENCE_PROCS = (
    "llama-server", "llama_server", "llama-cli", "ollama", "vllm", "sglang",
    "text-generation", "tabbyapi", "exllama", "koboldcpp", "python",
)


def _nvidia_gpu_memory() -> dict[str, dict]:
    """GPU UUID -> {index, name, vram_used_gb, vram_total_gb} (nvidia-smi)."""
    out = _sh([
        "nvidia-smi",
        "--query-gpu=uuid,index,name,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ])
    gpus: dict[str, dict] = {}
    for line in (out or "").splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 5 or not p[0]:
            continue
        gpus[p[0]] = {
            "index": _int(p[1]),
            "name": p[2],
            "vram_used_gb": round(_int(p[3]) / 1024, 1) if _int(p[3]) else 0.0,
            "vram_total_gb": round(_int(p[4]) / 1024, 1) if _int(p[4]) else None,
        }
    return gpus


def collect_gpu_usage() -> dict:
    """どのGPUで推論が走ったかを nvidia-smi のスナップショットから判定する.

    マルチGPU機では「3090で測ったのか5090で測ったのか」が分からないと tok/s に
    意味がない。また llama.cpp は ``/props`` にGPUオフロード情報を持たないため、
    プロセスのVRAM占有量が実質的なオフロード量の代理指標になる。

    実行後 (モデルがロードされたまま) に1回だけ呼ぶ想定。取得できなければ {}。
    """
    gpus = _nvidia_gpu_memory()
    if not gpus:
        return {}
    out = _sh([
        "nvidia-smi",
        "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory",
        "--format=csv,noheader,nounits",
    ])
    procs = []
    for line in (out or "").splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 4 or p[0] not in gpus:
            continue
        used = _int(p[3])
        g = gpus[p[0]]
        procs.append({
            "gpu_index": g["index"],
            "gpu_name": g["name"],
            "pid": _int(p[1]),
            "process": str(p[2]).split("/")[-1],
            "vram_gb": round(used / 1024, 1) if used else 0.0,
        })
    usage: dict = {}
    if procs:
        usage["processes"] = procs
        # 同一PIDが複数GPUに現れる = tensor split で分割ロードされている。
        # 「どちらのGPUか」ではなく「どう分割されたか」を記録する必要がある。
        infer = [p for p in procs
                 if any(k in p["process"].lower() for k in _INFERENCE_PROCS)]
        by_pid: dict[int | None, list[dict]] = {}
        for p in (infer or procs):
            by_pid.setdefault(p["pid"], []).append(p)
        # VRAM合計が最大のPIDを推論プロセスとみなす
        pid, shards = max(
            by_pid.items(), key=lambda kv: sum(s["vram_gb"] for s in kv[1])
        )
        shards = sorted(shards, key=lambda s: s["gpu_index"] or 0)
        inference = {
            "pid": pid,
            "process": shards[0]["process"],
            "vram_total_gb": round(sum(s["vram_gb"] for s in shards), 1),
            "multi_gpu": len(shards) > 1,
            "gpus": [{"index": s["gpu_index"], "name": s["gpu_name"],
                      "vram_gb": s["vram_gb"]} for s in shards],
        }
        if not infer:
            # プロセス名が既知の推論サーバに一致しない = 別用途の可能性がある
            inference["uncertain"] = True
        usage["inference"] = inference
    # 全GPUの使用量 (推論プロセスを特定できなくても手がかりになる)
    usage["gpus"] = [
        {"index": g["index"], "name": g["name"],
         "vram_used_gb": g["vram_used_gb"], "vram_total_gb": g["vram_total_gb"]}
        for g in sorted(gpus.values(), key=lambda g: g["index"] or 0)
    ]
    return usage


# ─────────── 計算バックエンド (CUDA / ROCm / Vulkan / Metal) の判別 ───────────
#
# llama.cpp の `/props` は build_info (例 "b10157-c6292cfb8") しか返さず、
# **どのバックエンドでビルドされたかは API から一切取れない**。しかし tok/s は
# CUDA / ROCm / Vulkan で大きく変わるため、ここを空欄にすると結果を比較できない。
# そこで推論プロセスがロードしている共有ライブラリから逆算する。
# 判定順は重要: CUDA/ROCm/SYCL ビルドが libvulkan を間接ロードしていても
# Vulkan と誤判定しないよう、専用ランタイムを先に見る。
_RUNTIME_LIBS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CUDA", ("libggml-cuda", "libcudart", "libcublas")),
    ("ROCm", ("libggml-hip", "libamdhip64", "librocblas", "libhipblas")),
    ("SYCL", ("libggml-sycl", "libsycl", "libmkl_sycl")),
    ("Vulkan", ("libggml-vulkan", "libvulkan")),
    ("Metal", ("libggml-metal",)),
    ("BLAS", ("libggml-blas", "libopenblas", "libmkl_rt")),
)
# 推論サーバのプロセス名 (実行ファイル名で照合する)
_SERVER_NAMES = ("llama-server", "llama_server", "ollama", "vllm", "sglang",
                 "koboldcpp", "tabbyapi")


def _proc_cmdlines() -> list[tuple[int, str]]:
    """(pid, cmdline) の一覧. Linux は /proc、macOS は ps から取る."""
    out: list[tuple[int, str]] = []
    if sys.platform.startswith("linux"):
        try:
            for name in os.listdir("/proc"):
                if not name.isdigit():
                    continue
                try:
                    with open(f"/proc/{name}/cmdline", "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode(
                            "utf-8", "replace"
                        ).strip()
                except Exception:
                    continue
                if cmd:
                    out.append((int(name), cmd))
        except Exception:
            return []
        return out
    # macOS / その他
    ps = _sh(["ps", "-Ao", "pid=,args="])
    for line in (ps or "").splitlines():
        line = line.strip()
        pid, _, cmd = line.partition(" ")
        if pid.isdigit() and cmd:
            out.append((int(pid), cmd.strip()))
    return out


def find_server_pid(port: int | None = None) -> int | None:
    """ローカルで動いている推論サーバの PID を探す.

    同じポートでビルドを差し替える運用を想定し、**ポート一致を最優先**する
    (CUDA版を落として ROCm版を上げた直後でも、今あがっている方を掴む)。
    """
    cands = [(pid, cmd) for pid, cmd in _proc_cmdlines()
             if any(n in cmd for n in _SERVER_NAMES)]
    if not cands:
        return None
    if port:
        for pid, cmd in cands:
            if f"--port {port}" in cmd or f"--port={port}" in cmd or \
                    f":{port}" in cmd:
                return pid
    return cands[0][0]


def _proc_exe(pid: int) -> str | None:
    """/proc/<pid>/exe が指す実行ファイルの実体パス (取れなければ None)."""
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except Exception:
        return None


def _proc_maps(pid: int) -> str | None:
    """/proc/<pid>/maps の内容 (自プロセス所有ならroot不要。無理なら None)."""
    try:
        with open(f"/proc/{pid}/maps", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def detect_runtime(pid: int | None) -> dict:
    """推論プロセスのロード済みライブラリから計算バックエンドを判別する.

    ``/proc/<pid>/maps`` は自プロセス所有なら root 不要で読める。
    ggml をバックエンド別 .so に分けたビルド (libggml-cuda.so 等) でも、
    静的リンクしたビルド (libcudart / libamdhip64 が直接見える) でも判る。
    """
    if not pid:
        return {}
    info: dict = {}
    exe = _proc_exe(pid)
    if exe:
        info["binary"] = exe
    libs: set[str] = set()
    for line in (_proc_maps(pid) or "").splitlines():
        path = line.rstrip("\n").split(" ", 5)[-1].strip()
        if path.startswith("/") and ".so" in path:
            libs.add(path.rsplit("/", 1)[-1])
    if libs:
        hits = []
        for label, keys in _RUNTIME_LIBS:
            matched = sorted({lib for lib in libs
                              for k in keys if lib.startswith(k)})
            if matched:
                hits.append((label, matched))
        if hits:
            info["compute"] = hits[0][0]
            info["evidence"] = hits[0][1]
            if len(hits) > 1:
                info["also_loaded"] = [h[0] for h in hits[1:]]
        else:
            info["compute"] = "CPU"
    # ライブラリを読めなくても、ビルドディレクトリ名は強い手がかりになる
    binpath = (info.get("binary") or "").lower()
    for label, key in (("CUDA", "cuda"), ("ROCm", "rocm"), ("ROCm", "hip"),
                       ("Vulkan", "vulkan"), ("SYCL", "sycl"),
                       ("Metal", "metal")):
        if key in binpath:
            info.setdefault("compute", label)
            info["binary_hint"] = label
            break
    return info


# ── 起動引数から推論構成を読む ──────────────────────────────────────────
#
# llama.cpp の /props は n_ctx と build_info しか返さず、**GPUオフロード量
# (-ngl) も使用デバイス (--device) も取れない**。しかし起動引数には全部書いて
# ある。CUDA / ROCm / Vulkan のどれでも同じ方法で読めるので、ここが最も確実。
_ARG_VALUE_KEYS = {
    "-ngl": "n_gpu_layers", "--n-gpu-layers": "n_gpu_layers",
    "--gpu-layers": "n_gpu_layers",
    "-c": "n_ctx", "--ctx-size": "n_ctx",
    "-t": "threads", "--threads": "threads",
    "-ts": "tensor_split", "--tensor-split": "tensor_split",
    "-mg": "main_gpu", "--main-gpu": "main_gpu",
    "-sm": "split_mode", "--split-mode": "split_mode",
    "-dev": "device", "--device": "device",
    "-np": "parallel", "--parallel": "parallel",
    "-b": "batch_size", "--batch-size": "batch_size",
    "-ub": "ubatch_size", "--ubatch-size": "ubatch_size",
    "--spec-type": "spec_type",
    "-md": "draft_model", "--model-draft": "draft_model",
}
_ARG_FLAGS = {
    "--mlock": "mlock", "--no-mmap": "no_mmap",
    "-fa": "flash_attn", "--flash-attn": "flash_attn",
    "-cb": "cont_batching", "--cont-batching": "cont_batching",
}
_INT_ARGS = ("n_gpu_layers", "n_ctx", "threads", "parallel", "main_gpu",
             "batch_size", "ubatch_size")
# 起動引数に混ざりうる秘匿値 (results.json は共有されうるので必ず伏せる)
_SECRET_ARGS = ("key", "token", "secret", "password", "passwd")
# 可視デバイスを絞る環境変数 (--device と併用されると実際の割当がずれる)
_VISIBLE_ENV = ("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES",
                "ROCR_VISIBLE_DEVICES", "GGML_VK_VISIBLE_DEVICES",
                "GPU_DEVICE_ORDINAL")


def parse_server_args(argv: list[str]) -> dict:
    """llama-server の argv から推論構成を抜き出す (秘匿値は伏せる)."""
    out: dict = {}
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in _ARG_FLAGS:
            out[_ARG_FLAGS[tok]] = True
            i += 1
            continue
        key = _ARG_VALUE_KEYS.get(tok)
        if key and i + 1 < len(argv):
            out[key] = argv[i + 1]
            i += 2
            continue
        i += 1
    for k in _INT_ARGS:
        if k in out and _int(out[k]) is not None:
            out[k] = _int(out[k])
    return out


def _redact_argv(argv: list[str]) -> str:
    """再現用に起動コマンドを1行で残す. --api-key 等の値は伏せる."""
    safe: list[str] = []
    redact_next = False
    for tok in argv:
        if redact_next:
            safe.append("***")
            redact_next = False
            continue
        low = tok.lower()
        if low.startswith("-") and any(s in low for s in _SECRET_ARGS):
            if "=" in tok:
                safe.append(tok.split("=", 1)[0] + "=***")
                continue
            safe.append(tok)
            redact_next = True
            continue
        safe.append(tok)
    return " ".join(safe)


def _proc_argv(pid: int) -> list[str]:
    """/proc/<pid>/cmdline を NUL 区切りで正しく分解する (空白入りパス対策)."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except Exception:
        return []
    return [a for a in raw.decode("utf-8", "replace").split("\x00") if a]


def _proc_visible_env(pid: int) -> dict:
    """可視デバイスを絞る環境変数だけを拾う (他の環境変数は秘匿情報を含みうる)."""
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            raw = f.read()
    except Exception:
        return {}
    env = {}
    for item in raw.decode("utf-8", "replace").split("\x00"):
        k, _, v = item.partition("=")
        if k in _VISIBLE_ENV and v:
            env[k] = v
    return env


def _vulkan_device_names() -> list[str]:
    """vulkaninfo --summary の列挙順のデバイス名 (Vulkan<N> の解決に使う)."""
    out = _sh(["vulkaninfo", "--summary"], timeout=20.0) or ""
    return [m.group(1).strip()
            for m in re.finditer(r"deviceName\s*=\s*(.+)", out)]


def resolve_device(dev: str, host_gpus: list[dict]) -> dict:
    """``ROCm0`` / ``Vulkan2`` / ``CUDA0`` を実GPU名に解決する."""
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", (dev or "").strip())
    if not m:
        return {"device": dev} if dev else {}
    kind, idx = m.group(1), int(m.group(2))
    info: dict = {"device": dev, "device_kind": kind, "device_index": idx}
    low = kind.lower()
    if low in ("cuda", "rocm", "hip"):
        vendor = "nvidia" if low == "cuda" else "amd"
        pool = [g for g in host_gpus if g.get("vendor") == vendor]
        if idx < len(pool):
            info["device_name"] = pool[idx].get("name")
    elif low == "vulkan":
        names = _vulkan_device_names()
        if idx < len(names):
            info["device_name"] = names[idx]
        elif idx < len(host_gpus):
            # vulkaninfo が無い環境。ggml の Vulkan 列挙順は概ね PCI 順なので
            # 搭載順で当てるが、確証がないことを明示する。
            info["device_name"] = host_gpus[idx].get("name")
            info["device_name_uncertain"] = True
    return info


def collect_launch(pid: int | None, host_gpus: list[dict] | None = None) -> dict:
    """推論サーバの起動構成 (デバイス・-ngl・n_ctx 等) を収集する."""
    if not pid:
        return {}
    argv = _proc_argv(pid)
    if not argv:
        return {}
    launch = parse_server_args(argv)
    launch["command"] = _redact_argv(argv)
    dev = launch.pop("device", None)
    if dev:
        launch.update(resolve_device(str(dev), host_gpus or []))
    env = _proc_visible_env(pid)
    if env:
        launch["visible_devices_env"] = env
    return launch


def _gpu_amd() -> list[dict]:
    """AMD GPU を列挙する (ROCm / Vulkan で iGPU・Radeon を使う場合に必要).

    nvidia-smi しか見ていないと、ROCm や Vulkan で Radeon を使った実行で
    GPU欄が空になる。rocm-smi があればそれを、無ければ lspci を使う。
    """
    gpus: list[dict] = []
    csv = _sh(["rocm-smi", "--showproductname", "--csv"], timeout=15.0)
    if csv:
        lines = [ln for ln in csv.splitlines() if ln.strip()]
        if len(lines) >= 2:
            head = [h.strip().lower() for h in lines[0].split(",")]
            for ln in lines[1:]:
                cells = [c.strip() for c in ln.split(",")]
                row = dict(zip(head, cells))
                name = (row.get("card series") or row.get("card model")
                        or row.get("card sku") or "")
                if name and not name.lower().startswith("n/a"):
                    gpus.append({"name": name, "vendor": "amd"})
    if gpus:
        mem = _sh(["rocm-smi", "--showmeminfo", "vram", "--csv"], timeout=15.0)
        for ln in (mem or "").splitlines()[1:]:
            cells = [c.strip() for c in ln.split(",")]
            tot = next((_int(c) for c in cells[1:] if _int(c)), None)
            idx = len([g for g in gpus if "vram_gb" in g])
            if tot and idx < len(gpus):
                gpus[idx]["vram_gb"] = round(tot / (1024 ** 3), 1)
        return gpus
    # rocm-smi が無い環境向けフォールバック
    out = _sh(["lspci", "-mm"], timeout=10.0) or ""
    for line in out.splitlines():
        if not any(k in line for k in ("VGA compatible", "Display controller",
                                       "3D controller")):
            continue
        if "AMD" not in line and "ATI" not in line:
            continue
        # -mm の並びは class, vendor, device, subvendor, subdevice。
        # デバイス名 (fields[2]) が製品名なのでそれを使う。
        fields = re.findall(r'"([^"]*)"', line)
        if len(fields) >= 3 and fields[2]:
            gpus.append({"name": fields[2], "vendor": "amd"})
    return gpus


def _cuda_version() -> str | None:
    out = _sh(["nvidia-smi", "--query", "--display=COMPUTE"]) or ""
    m = re.search(r"CUDA Version\s*:\s*([\d.]+)", out)
    if m:
        return m.group(1)
    out2 = _sh(["nvcc", "--version"]) or ""
    m2 = re.search(r"release ([\d.]+)", out2)
    return m2.group(1) if m2 else None


def _host_macos() -> dict:
    h: dict = {
        "cpu": _sysctl("machdep.cpu.brand_string") or platform.processor() or None,
        "cpu_cores": _int(_sysctl("hw.ncpu")),
        "ram_gb": _gb(_sysctl("hw.memsize")),
    }
    # Apple Silicon は P/E コア構成まで残すと比較に効く
    p = _int(_sysctl("hw.perflevel0.physicalcpu"))
    e = _int(_sysctl("hw.perflevel1.physicalcpu"))
    if p:
        h["cpu_cores_perf"] = p
    if e:
        h["cpu_cores_eff"] = e
    h["gpu"] = _gpu_macos()
    h["unified_memory"] = platform.machine() == "arm64"
    return h


def _host_linux() -> dict:
    h: dict = {"cpu": None, "cpu_cores": None, "ram_gb": None}
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        m = re.search(r"^model name\s*:\s*(.+)$", text, re.M)
        if m:
            h["cpu"] = m.group(1).strip()
        h["cpu_cores"] = text.count("\nprocessor") + (
            1 if text.startswith("processor") else 0
        ) or None
    except Exception:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8", errors="ignore") as f:
            m = re.search(r"^MemTotal:\s*(\d+) kB", f.read(), re.M)
        if m:
            h["ram_gb"] = round(int(m.group(1)) / (1024 ** 2), 1)
    except Exception:
        pass
    # NVIDIA だけを見ていると、ROCm/Vulkan で Radeon (iGPU含む) を使った実行で
    # GPU欄が空になる。AMD側も列挙する。
    h["gpu"] = _gpu_nvidia() + _gpu_amd()
    cuda = _cuda_version()
    if cuda:
        h["cuda"] = cuda
    return h


def collect_host() -> dict:
    """ホストのハード/OS情報を返す. 失敗しても最低限のキーは埋める."""
    host: dict = {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
    }
    try:
        if sys.platform == "darwin":
            host["os"] = f"macOS {platform.mac_ver()[0] or platform.release()}"
            host.update(_host_macos())
        elif sys.platform.startswith("linux"):
            host.update(_host_linux())
        else:
            host["cpu"] = platform.processor() or None
            host["gpu"] = _gpu_nvidia()
    except Exception as e:  # 収集失敗はベンチを止めない
        host["collect_error"] = f"{type(e).__name__}: {e}"
    return {k: v for k, v in host.items() if v not in (None, [], "")}


# ─────────────────────── 推論バックエンド (構成の実測) ───────────────────────


def _backend_ollama(base_url: str, model: str | None) -> dict:
    """Ollama の /api/ps と /api/show からロード中モデルの実構成を取る.

    /api/ps の size_vram / size がGPUオフロード率になる (ここが tok/s を支配する)。
    """
    b: dict = {"kind": "ollama", "base_url": base_url}
    url = base_url.rstrip("/")
    ps = _get_json(f"{url}/api/ps") or {}
    loaded = ps.get("models") or []
    entry = None
    if model:
        entry = next((m for m in loaded if m.get("name") == model
                      or m.get("model") == model), None)
    entry = entry or (loaded[0] if loaded else None)
    if entry:
        b["model"] = entry.get("name") or entry.get("model")
        size = _int(entry.get("size"))
        vram = _int(entry.get("size_vram"))
        if size:
            b["weights_gb"] = round(size / (1024 ** 3), 1)
        if vram is not None and size:
            b["vram_resident_gb"] = round(vram / (1024 ** 3), 1)
            b["gpu_offload_ratio"] = round(vram / size, 3)
        det = entry.get("details") or {}
        for src, dst in (("quantization_level", "quantization"),
                         ("parameter_size", "parameter_size"),
                         ("family", "family")):
            if det.get(src):
                b[dst] = det[src]
        ctx = _int(entry.get("context_length"))
        if ctx:
            b["n_ctx"] = ctx
    elif model:
        b["model"] = model
        b["note"] = (
            "ロード中モデルなし (/api/ps が空) — モデル未ロード、"
            "または生成が全て失敗した可能性"
        )
    ver = _get_json(f"{url}/api/version") or {}
    if ver.get("version"):
        b["server_version"] = f"ollama {ver['version']}"
    return b


def _backend_openai(base_url: str, model: str | None) -> dict:
    """OpenAI互換サーバ. ローカル (llama.cpp / LM Studio 等) なら /props も見る."""
    local = _is_local_url(base_url)
    b: dict = {
        "kind": "llama.cpp/openai-compat" if local else "openai-compat-api",
        "base_url": base_url,
    }
    if model:
        b["model"] = model
    if not local:
        return b
    # llama.cpp server: /props に n_ctx・モデルパス・ビルド情報が入っている
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    props = _get_json(f"{root}/props")
    if not isinstance(props, dict):
        return b
    b["kind"] = "llama.cpp"
    gen = props.get("default_generation_settings") or {}
    n_ctx = _int(gen.get("n_ctx") or props.get("n_ctx"))
    if n_ctx:
        b["n_ctx"] = n_ctx
    slots = _int(props.get("total_slots"))
    if slots:
        b["parallel_slots"] = slots
    path = props.get("model_path") or gen.get("model") or props.get("model_path")
    if path:
        b["model_path"] = str(path)
        # ggufファイル名に量子化が入っている (例: ...-Q4_K_M.gguf)
        m = re.search(r"(IQ\d[A-Z_]*|Q\d[A-Z0-9_]*|F16|BF16|F32)", str(path))
        if m:
            b["quantization"] = m.group(1)
    for key in ("build_info", "chat_template_name"):
        if props.get(key):
            b[key] = props[key]
    return b


def collect_backend(cfg: dict | None, served_model: str | None = None) -> dict:
    """モデル設定 (config の models.<name>) からバックエンド構成を収集する.

    cfg は resolve_model() の戻り値を想定。api_key は読まない/含めない。
    """
    cfg = cfg or {}
    ctype = (cfg.get("type") or "openai").lower()
    model = served_model or cfg.get("model") or None
    if model and str(model).lower() == "auto":
        model = served_model or None
    base_url = cfg.get("base_url") or ""
    try:
        if ctype == "ollama":
            return _backend_ollama(base_url or "http://localhost:11434", model)
        if ctype == "openai":
            return _backend_openai(base_url, model)
        if ctype == "cli":
            b = {"kind": f"cli:{cfg.get('preset', 'custom')}"}
            if model:
                b["model"] = model
            return b
        if ctype == "mock":
            return {"kind": "mock"}
        b = {"kind": ctype}
        if base_url:
            b["base_url"] = base_url
        if model:
            b["model"] = model
        return b
    except Exception as e:
        return {"kind": ctype, "collect_error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────── まとめ ───────────────────────────────


def _execution_kind(cfg: dict) -> tuple[str, str]:
    """(execution, note) を返す. note はレポートに出す誤解防止の一文."""
    ctype = (cfg.get("type") or "openai").lower()
    if ctype == "mock":
        return "mock", "モック実行 (性能計測の対象外)"
    if ctype == "cli":
        return (
            "subscription-cli",
            "サブスクCLI経由。推論はベンダ側で実行されるため、"
            "下記ホストのスペックは生成速度に影響しない",
        )
    if ctype == "ollama":
        return "local", "ローカル推論 (このホストのGPU/メモリが生成速度を決める)"
    if _is_local_url(cfg.get("base_url") or ""):
        return "local", "ローカル推論 (このホストのGPU/メモリが生成速度を決める)"
    return (
        "remote-api",
        "クラウドAPI推論。推論はベンダ側のハードで実行されるため、"
        "下記ホストのスペックは生成速度に影響しない (計測クライアントの情報)",
    )


def collect(cfg: dict | None = None, served_model: str | None = None) -> dict:
    """実行環境メタデータを1つの dict にまとめて返す (例外を出さない)."""
    cfg = cfg or {}
    try:
        execution, note = _execution_kind(cfg)
        host = collect_host()
        backend = collect_backend(cfg, served_model)
        if execution == "local":
            # サーバのPIDを起点に構成を集める。ポート一致を最優先で探すので、
            # 同じポートでビルドを差し替える運用でも今あがっている方を掴む。
            pid = find_server_pid(_port_of(cfg.get("base_url") or ""))
            usage = collect_gpu_usage()
            pid = pid or ((usage.get("inference") or {}).get("pid")
                          if usage else None)

            # 計算バックエンド (CUDA / ROCm / Vulkan / …)。
            # config に runtime: を書いていればそれを正とし、検出は裏付けに回す
            # (同じポートでビルドを差し替える運用では書き忘れが起きるため、
            #  検出値と食い違ったら両方を残して気付けるようにする)。
            runtime = detect_runtime(pid)
            declared = cfg.get("runtime")
            if declared:
                detected = runtime.get("compute")
                runtime["compute"] = str(declared)
                runtime["source"] = "config"
                if detected and detected.lower() != str(declared).lower():
                    runtime["detected"] = detected
                    runtime["mismatch"] = True
            elif runtime.get("compute"):
                runtime["source"] = "detected"
            if runtime:
                backend["runtime"] = runtime

            # 起動引数 (--device / -ngl / --ctx-size …)。llama.cpp では
            # /props にGPUオフロード情報が無く、-ngl が実質的なオフロード量。
            launch = collect_launch(pid, host.get("gpu") or [])
            if launch:
                backend["launch"] = launch

            if usage:
                # ROCm/Vulkan ビルドでも nvidia-smi の compute-apps に数十MiBで
                # 顔を出すことがあり、それを推論GPUと誤認すると「Radeonで動いて
                # いるのに RTX 3090」と出る。CUDA以外では紐づけを採用しない。
                compute = (runtime.get("compute") or "").lower()
                if compute and not compute.startswith("cuda"):
                    usage.pop("inference", None)
                    usage["note"] = (
                        f"計算バックエンドが {runtime.get('compute')} のため、"
                        "nvidia-smi 由来の推論GPU判定は採用していない"
                    )
                backend["gpu_usage"] = usage
        return {
            "execution": execution,
            "note": note,
            "host": host,
            "backend": backend,
        }
    except Exception as e:
        return {"execution": "unknown",
                "collect_error": f"{type(e).__name__}: {e}"}


def format_summary(env: dict) -> str:
    """1行サマリ (実行ログ用). 例: 'Apple M3 Max / 128GB / Q4_K_M / GPU 100%'."""
    if not env:
        return ""
    host = env.get("host") or {}
    backend = env.get("backend") or {}
    parts: list[str] = []
    # リモート推論ではホストのスペックは速度に無関係 → 出さない (誤読防止)
    if env.get("execution") not in ("local", None, ""):
        for key in ("kind", "model"):
            if backend.get(key):
                parts.append(str(backend[key]))
        parts.append("推論はリモート実行")
        return " / ".join(parts)
    # 起動引数で指定されたデバイスが最も確実 (ROCm/Vulkan でも取れる)
    launch = backend.get("launch") or {}
    inf = (backend.get("gpu_usage") or {}).get("inference") or {}
    if launch.get("device"):
        parts.append(launch.get("device_name") or launch["device"])
        ngl = launch.get("n_gpu_layers")
        if ngl == 0:
            parts.append("⚠️ -ngl 0 (GPU未使用)")
        elif ngl is not None:
            parts.append(f"-ngl {ngl}")
    elif inf.get("gpus"):
        parts.append(" + ".join(
            f"{g.get('name', 'GPU')} {g.get('vram_gb', 0)}GB"
            for g in inf["gpus"]
        ) + (f" (計{inf.get('vram_total_gb')}GB を分割)"
             if inf.get("multi_gpu") else ""))
    elif host.get("gpu"):
        g = (host.get("gpu") or [])[0]
        name = g.get("name") or "GPU"
        if g.get("cores"):
            name += f" {g['cores']}core"
        if g.get("vram_gb"):
            name += f" {g['vram_gb']}GB"
        parts.append(name)
    elif host.get("cpu"):
        parts.append(host["cpu"])
    if host.get("ram_gb"):
        parts.append(f"RAM {host['ram_gb']}GB")
    rt = backend.get("runtime") or {}
    if rt.get("compute"):
        parts.append(str(rt["compute"]))
    if backend.get("quantization"):
        parts.append(str(backend["quantization"]))
    ratio = backend.get("gpu_offload_ratio")
    if ratio is not None:
        parts.append(f"GPU offload {ratio * 100:.0f}%")
    if backend.get("n_ctx"):
        parts.append(f"n_ctx {backend['n_ctx']}")
    return " / ".join(parts)
