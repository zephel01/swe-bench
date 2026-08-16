#!/usr/bin/env python3
"""gguf_probe.py の出力 (gguf.json) から、実際の起動設定に落とし込む.

    python gguf_probe.py --json --out gguf.json /path/to/*.gguf   # 先にこれ
    python gguf_plan.py gguf.json --vram 24                       # 何が載るか一覧
    python gguf_plan.py gguf.json --vram 24 --pick Q5_K_M         # 起動コマンドを出す
    python gguf_plan.py gguf.json --vram 24 --pick Q5_K_M --ctx 131072

決めてくれるもの:

  * `--ctx-size`      … VRAM 予算から逆算した上限 (native ctx も超えない)
  * `-ctk / -ctv`     … f16 で入らないとき q8_0 を提案する
  * `--spec-type`     … MTP テンソルがあるときだけ draft-mtp を付ける
  * サンプリング一式  … chat_template が thinking なら Qwen3.8 公式推奨

--- 単位について (ここを間違えると全部ずれる) ---

GGUF の `size_gb` は **バイト ÷ 10^9 (GB)**。一方 GPU の「24GB」は
**GiB (÷ 2^30)**。24GB のカードは 10^9 換算だと 25.77 GB ある。
このスクリプトは**すべて GiB に揃えて**計算する。

--- VRAM の見積り式 ---

    使用量 = モデルファイル + KVキャッシュ + オーバーヘッド

オーバーヘッド (計算バッファ・CUDAコンテキスト・投機デコードのバッファ) は
実測1点から較正した:

    Qwen3.8-27B Q5_K_M / ctx 65536 / KV f16 / -fa on / --spec-type draft-mtp
      ファイル 18.47 GiB + KV 4.25 GiB = 22.72 GiB
      実測 (llama-server) 23.5 GiB
      → オーバーヘッド 0.78 GiB

較正点が1つしかないので、既定は安全側に **1.0 GiB** を置く。
実測が増えたら `--overhead` で上書きすること。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GIB = 1024 ** 3
#: 量子化KVキャッシュのサイズ比 (8bit + スケール)。gguf_probe と同じ値
Q8_FACTOR = 0.53
#: 実測1点から較正したオーバーヘッド (GiB)。安全側に丸めてある
DEFAULT_OVERHEAD_GIB = 1.0
#: --ctx-size はこの単位に切り下げる
CTX_STEP = 4096

THINKING_SAMPLING = {
    "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
}
NON_THINKING_SAMPLING = {
    "temperature": 0.7, "top_p": 0.80, "top_k": 20,
}


def file_gib(rec: dict) -> float:
    return rec["size_gb"] * 1e9 / GIB


def kv_gib(rec: dict, ctx: int, kv_mode: str) -> float:
    per_tok = (rec.get("kv_cache") or {}).get("bytes_per_token_f16")
    if not per_tok:
        return 0.0
    factor = Q8_FACTOR if kv_mode == "q8_0" else 1.0
    return per_tok * ctx * factor / GIB


def max_ctx(rec: dict, vram_gib: float, kv_mode: str, overhead: float) -> int:
    """VRAM 予算に収まる最大の ctx。native ctx を超えない。CTX_STEP に切り下げ。"""
    per_tok = (rec.get("kv_cache") or {}).get("bytes_per_token_f16")
    if not per_tok:
        return 0
    factor = Q8_FACTOR if kv_mode == "q8_0" else 1.0
    budget = (vram_gib - overhead - file_gib(rec)) * GIB
    if budget <= 0:
        return 0
    n = int(budget / (per_tok * factor))
    n -= n % CTX_STEP
    native = rec.get("context_length") or n
    return max(0, min(n, native))


def short(rec: dict) -> str:
    return rec["file"].replace(".gguf", "")


def cmd_table(recs, vram, overhead, ctx_req):
    rows = []
    for r in sorted(recs, key=lambda d: d["size_gb"]):
        f16 = max_ctx(r, vram, "f16", overhead)
        q8 = max_ctx(r, vram, "q8_0", overhead)
        fit = ""
        if ctx_req:
            need_f16 = file_gib(r) + kv_gib(r, ctx_req, "f16") + overhead
            need_q8 = file_gib(r) + kv_gib(r, ctx_req, "q8_0") + overhead
            if need_f16 <= vram:
                fit = f"f16でOK ({need_f16:.1f})"
            elif need_q8 <= vram:
                fit = f"q8_0ならOK ({need_q8:.1f})"
            else:
                fit = f"入らない ({need_q8:.1f})"
        rows.append((short(r), file_gib(r), f16, q8, fit))

    w = max(len(x[0]) for x in rows) + 2
    head = f"{'量子化':<{w}}{'ファイル':>9}{'最大ctx(f16)':>14}{'最大ctx(q8_0)':>15}"
    if ctx_req:
        head += f"   ctx {ctx_req:,} は?"
    print(head)
    print("-" * len(head))
    for name, fg, f16, q8, fit in rows:
        f16s = f"{f16:,}" if f16 else "入らない"
        q8s = f"{q8:,}" if q8 else "入らない"
        line = f"{name:<{w}}{fg:>8.2f}G{f16s:>14}{q8s:>15}"
        if ctx_req:
            line += f"   {fit}"
        print(line)


def emit_config(rec: dict, ctx: int, kv_mode: str, vram: float, overhead: float,
                model_path: str, port: int, device: str) -> str:
    think = rec.get("chat_template_has_think")
    samp = THINKING_SAMPLING if think else NON_THINKING_SAMPLING
    mtp = bool(rec.get("mtp_tensor_count"))
    used = file_gib(rec) + kv_gib(rec, ctx, kv_mode) + overhead
    # max_tokens は ctx の 3/4 を上限に。プロンプト分を残す
    max_tokens = min(49152, (ctx * 3 // 4) // 1024 * 1024)

    L = []
    L.append(f"# ===== {short(rec)} / ctx {ctx:,} / KV {kv_mode} =====")
    L.append(f"# 見積り: モデル {file_gib(rec):.2f} + KV {kv_gib(rec, ctx, kv_mode):.2f} "
             f"+ オーバーヘッド {overhead:.2f} = {used:.2f} GiB / 予算 {vram:.1f} GiB")
    L.append(f"# native ctx = {rec.get('context_length', 0):,}"
             + ("  / rope scaling なし" if not rec.get("rope_scaling_type") else
                f"  / rope scaling: {rec.get('rope_scaling_type')}"))
    if rec.get("is_hybrid_attention"):
        L.append(f"# ハイブリッド注意: {len(rec['kv_layers'])}/{rec['kv_cache']['total_layers']} 層のみ "
                 f"KV 保持 = {rec['kv_cache']['bytes_per_token_f16'] / 1024:.0f} KB/token")
    L.append("")
    L.append("# --- llama-server ---")
    # 注記は**コマンドの外**に出す。継続行 (\) の途中に # を書くと
    # そこから行末までがコメントになり、\ ごと消えてコマンドが壊れる。
    if kv_mode == "q8_0":
        L.append("# -ctk/-ctv の量子化には -fa on が必須 (下に含めてある)")
    if mtp:
        L.append(f"# MTP テンソルを {rec['mtp_tensor_count']} 本確認 → --spec-type draft-mtp を付ける")
    else:
        L.append("# MTP テンソルなし → --spec-type draft-mtp は付けない")
    args = [
        f"llama-server -m {model_path}",
        f"--port {port} --device {device}",
        "-ngl 99 -fa on",
        f"--ctx-size {ctx} --parallel 1",
        "--batch-size 2048 --ubatch-size 512",
    ]
    if kv_mode == "q8_0":
        args.append("-ctk q8_0 -ctv q8_0")
    if mtp:
        args.append("--spec-type draft-mtp")
    L.append(" \\\n  ".join(args))
    L.append("")
    L.append("# --- config.yaml (models: の下) ---")
    L.append(f"  {short(rec).lower().replace('.', '-')}:")
    L.append("    type: openai")
    L.append(f'    base_url: "http://localhost:{port}/v1"')
    L.append('    model: "auto"')
    L.append('    api_key: "sk-local"')
    for k, v in samp.items():
        L.append(f"    {k}: {v}")
    L.append(f"    max_tokens: {max_tokens}   # ctx {ctx:,} の 3/4。プロンプト分を残す")
    L.append("    seed: 42          # runs: 1 のときだけ書く (runs>1 は毎回ランダムにする)")
    tag = "thinking" if think else "non-thinking"
    L.append(f"    # サンプリングは chat_template の判定 ({tag}) に基づく既定値")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="gguf_probe の JSON から llama-server / config.yaml の設定を出す")
    ap.add_argument("json_path", help="gguf_probe.py --json --out で作った JSON")
    ap.add_argument("--vram", type=float, required=True,
                    help="使える VRAM (GiB)。24GBのカードなら 24")
    ap.add_argument("--overhead", type=float, default=DEFAULT_OVERHEAD_GIB,
                    help=f"計算バッファ等の見込み (GiB, 既定 {DEFAULT_OVERHEAD_GIB})")
    ap.add_argument("--ctx", type=int, default=None,
                    help="使いたい ctx。指定すると各量子化が入るか判定する")
    ap.add_argument("--pick", default=None,
                    help="ファイル名の一部。指定すると起動コマンドと config を出す")
    ap.add_argument("--kv", choices=["f16", "q8_0", "auto"], default="auto",
                    help="KVキャッシュの型 (既定 auto = f16 で入らなければ q8_0)")
    ap.add_argument("--model-path", default=None, help="起動コマンドに書くパス")
    ap.add_argument("--port", type=int, default=8085)
    ap.add_argument("--device", default="CUDA0")
    args = ap.parse_args()

    recs = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    if isinstance(recs, dict):
        recs = [recs]
    lm = [r for r in recs if r.get("is_language_model") and r.get("kv_cache")]
    if not lm:
        sys.exit("言語モデルの記録が見つかりません（gguf_probe --json の出力を渡してください）")

    if not args.pick:
        print(f"VRAM 予算 {args.vram:.1f} GiB / オーバーヘッド {args.overhead:.2f} GiB\n")
        cmd_table(lm, args.vram, args.overhead, args.ctx)
        print("\n※ 数値はすべて GiB。GGUF の size_gb (バイト÷10^9) とは違うので注意")
        print("※ --pick <名前の一部> で起動コマンドと config.yaml を出します")
        return 0

    hits = [r for r in lm if args.pick.lower() in r["file"].lower()]
    if not hits:
        sys.exit(f"--pick {args.pick!r} に一致するファイルがありません: "
                 + ", ".join(short(r) for r in lm))
    if len(hits) > 1:
        sys.exit(f"--pick {args.pick!r} が複数に一致します: "
                 + ", ".join(short(r) for r in hits))
    rec = hits[0]

    kv_mode = args.kv
    ctx = args.ctx
    if kv_mode == "auto":
        kv_mode = "f16"
        if ctx and file_gib(rec) + kv_gib(rec, ctx, "f16") + args.overhead > args.vram:
            kv_mode = "q8_0"
            print(f"# ※ ctx {ctx:,} は f16 では入らないので KV を q8_0 にしました",
                  file=sys.stderr)
    if ctx is None:
        ctx = max_ctx(rec, args.vram, kv_mode, args.overhead)
        if not ctx:
            sys.exit(f"{short(rec)} は VRAM {args.vram} GiB に入りません "
                     f"(モデルだけで {file_gib(rec):.2f} GiB)")
        print(f"# ※ ctx 未指定なので予算いっぱいの {ctx:,} にしました", file=sys.stderr)

    used = file_gib(rec) + kv_gib(rec, ctx, kv_mode) + args.overhead
    if used > args.vram:
        print(f"# ⚠️ 見積り {used:.2f} GiB が予算 {args.vram:.1f} GiB を超えています",
              file=sys.stderr)

    mp = args.model_path or f"/path/to/{rec['file']}"
    print(emit_config(rec, ctx, kv_mode, args.vram, args.overhead,
                      mp, args.port, args.device))
    return 0


if __name__ == "__main__":
    sys.exit(main())
