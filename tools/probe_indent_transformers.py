#!/usr/bin/env python3
"""safetensors を transformers で直読みして、インデント潰れの有無を見る.

GGUF を一切経由しない経路。llama.cpp 側 (tools/probe_indent_tokens.py) と
同じ判定・同じ観点 (空白トークンの内訳) で比較できるようにしてある。

    python3 tools/probe_indent_transformers.py -n 3 --show 14
    python3 tools/probe_indent_transformers.py --model Jackrong/Qwopus3.8-27B-Flash
    python3 tools/probe_indent_transformers.py --self-test   # モデル不要の内部テスト

切り分け:
  * 262 '   ' / 285 / 309 のような階層別インデントトークンを使う (4スペース)
      → GGUF 変換が犯人 (H3c)。重みは無事
  * id 220 ' ' に潰す (1スペース)
      → 重みが犯人 (H3a)

メモリ: 27B を bf16 で載せると約54GB。足りなければ device_map="auto" が
CPU にオフロードする (遅いが3回生成するだけなので問題ない)。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_indent_tokens import (  # noqa: E402
    DEFAULT_PROMPT,
    indent_stats,
    self_test,
    verdict_for,
)


def run(args: argparse.Namespace) -> int:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"ERROR: transformers/torch が入っていない: {e}", file=sys.stderr)
        return 2

    print(f"  loading {args.model} (dtype={args.dtype}, device_map={args.device_map}) ...")
    tok = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=args.trust_remote_code
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=getattr(torch, args.dtype),
        device_map=args.device_map,
        trust_remote_code=args.trust_remote_code,
    )
    model.eval()

    text = tok.apply_chat_template(
        [{"role": "user", "content": args.prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tok(text, return_tensors="pt").to(model.device)
    prompt_len = inputs["input_ids"].shape[-1]

    tally: dict[str, int] = {}
    ws_tally: dict[tuple[int, str], int] = {}

    for i in range(1, args.n + 1):
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=args.temp > 0,
                temperature=args.temp if args.temp > 0 else None,
                pad_token_id=tok.pad_token_id or tok.eos_token_id,
            )
        new_ids = out[0][prompt_len:].tolist()
        content = tok.decode(new_ids, skip_special_tokens=True)

        for t in new_ids:
            pc = tok.decode([t], skip_special_tokens=False)
            if pc and not pc.strip():
                ws_tally[(t, pc)] = ws_tally.get((t, pc), 0) + 1

        v = verdict_for(content)
        tally[v] = tally.get(v, 0) + 1
        n1, n4 = indent_stats(content)
        print(f"  #{i:<3} {v:<10} [1sp={n1} 4sp={n4}] tokens={len(new_ids)}")
        if v != "ok" and args.show:
            print("    ---- content ----")
            for ln in content.splitlines()[: args.show]:
                print(f"    |{ln}")

    total = sum(tally.values())
    print("\n  ---- " + ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    collapsed = tally.get("COLLAPSED", 0) + tally.get("MIXED", 0)
    print(f"  潰れ発生率: {collapsed}/{total}")
    if ws_tally:
        print("  空白のみトークンの内訳 (id, 文字列, 出現回数):")
        for (t, pc), c in sorted(ws_tally.items(), key=lambda kv: -kv[1]):
            print(f"    {t:>7}  {pc!r:<14} x{c}")
    if collapsed:
        print("  → GGUF を経由しない経路でも潰れる。**重みが原因 (H3a)**。"
              " このモデルはコード用途では諦める")
    else:
        print("  → GGUF を経由しなければ正常。**配布 GGUF の変換が原因 (H3c)**。"
              " 上流に報告する価値がある")
    return 1 if collapsed else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--model", default="Jackrong/Qwopus3.8-27B-Flash")
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("--temp", type=float, default=0.0, help="0 で greedy")
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--dtype", default="bfloat16",
                    choices=("bfloat16", "float16", "float32"))
    ap.add_argument("--device-map", default="auto")
    ap.add_argument("--trust-remote-code", action="store_true")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--show", type=int, default=0, metavar="N")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
