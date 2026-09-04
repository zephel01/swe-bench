#!/usr/bin/env python3
"""インデント潰れが「モデルの出力」か「デトークナイズ」かを切り分ける.

llama-server に同じプロンプトを N 回投げ、
  (1) 潰れ (行頭が1スペースのみ) の発生率
  (2) 生成トークンID列を1個ずつ /detokenize した文字列の連結が、
      サーバが返した content と一致するか
を見る。

判定:
  * 連結 == content で、行頭のトークンが単一スペース
      → **モデル/量子化がそのトークンを選んでいる**。重み側の問題。
        Q5_K_M など別量子化・別ビルドと比較する。
  * 連結 != content (連結側は4スペース等)
      → **デトークナイズ/集約の問題**。llama.cpp 側のバグを疑う。
        gguf の vocab / pre-tokenizer を確認する。

使い方:
    python3 tools/probe_indent_tokens.py --url http://localhost:8085 -n 10
    python3 tools/probe_indent_tokens.py --url http://localhost:8085 -n 10 --temp 0.35
    python3 tools/probe_indent_tokens.py --self-test     # サーバ不要の内部テスト
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

DEFAULT_PROMPT = (
    "以下の仕様で Python 関数を1つだけ書いてください。説明は不要、"
    "```python コードブロックだけを返してください。\n\n"
    "仕様: 整数のリストを受け取り、連続する重複を取り除いたリストを返す "
    "`squeeze(items)` を書く。空リストは空リストを返す。"
    "ループの中に if を入れたネストのある実装にすること。\n"
)

INDENT_1SP = re.compile(r"^ [^ \t]", re.MULTILINE)
INDENT_4SP = re.compile(r"^    [^ \t]", re.MULTILINE)


def indent_stats(text: str) -> tuple[int, int]:
    return len(INDENT_1SP.findall(text)), len(INDENT_4SP.findall(text))


def verdict_for(text: str) -> str:
    n1, n4 = indent_stats(text)
    if n1 and not n4:
        return "COLLAPSED"
    if n1 and n4:
        return "MIXED"
    return "ok"


def post(url: str, path: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def render_prompt(url: str, user_text: str, timeout: float) -> str:
    """/apply-template があれば chat template を通す. 無ければ素通し."""
    try:
        r = post(url, "/apply-template",
                 {"messages": [{"role": "user", "content": user_text}]}, timeout)
        return r.get("prompt", user_text)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
        print("  (注) /apply-template が使えないので素のプロンプトで送る")
        return user_text


def piece_of(url: str, tok: int, cache: dict[int, str], timeout: float) -> str:
    if tok not in cache:
        r = post(url, "/detokenize", {"tokens": [tok]}, timeout)
        cache[tok] = r.get("content", "")
    return cache[tok]


def run_probe(args: argparse.Namespace) -> int:
    prompt = render_prompt(args.url, args.prompt, args.timeout)
    cache: dict[int, str] = {}
    tally: dict[str, int] = {}
    ws_tally: dict[tuple[int, str], int] = {}
    indent_mismatches = 0
    other_mismatches = 0

    for i in range(1, args.n + 1):
        r = post(args.url, "/completion", {
            "prompt": prompt,
            "n_predict": args.n_predict,
            "temperature": args.temp,
            "return_tokens": True,
            "cache_prompt": False,
        }, args.timeout)
        content = r.get("content", "")
        tokens = r.get("tokens") or []
        v = verdict_for(content)
        tally[v] = tally.get(v, 0) + 1

        note = ""
        if tokens:
            pieces = [piece_of(args.url, t, cache, args.timeout) for t in tokens]
            joined = "".join(pieces)
            jn1, jn4 = indent_stats(joined)
            cn1, cn4 = indent_stats(content)
            # 空白だけのトークン (インデント由来) の内訳
            for t, pc in zip(tokens, pieces):
                if pc and not pc.strip():
                    ws_tally[(t, pc)] = ws_tally.get((t, pc), 0) + 1
            if (jn1, jn4) != (cn1, cn4):
                # インデント統計そのものが違う = 文字列化で空白が変わっている
                indent_mismatches += 1
                note = (f"  ⚠ インデント統計が不一致  連結[1sp={jn1} 4sp={jn4}]"
                        f" content[1sp={cn1} 4sp={cn4}]")
            elif joined != content:
                # 空白以外の差 (特殊トークンの表示など)。位置だけ出す
                k = next(i for i, (a, b) in enumerate(zip(joined, content)) if a != b) \
                    if any(a != b for a, b in zip(joined, content)) \
                    else min(len(joined), len(content))
                other_mismatches += 1
                note = (f"  (連結≠content だがインデント統計は一致。差分位置 {k}:"
                        f" 連結={joined[k:k+20]!r} content={content[k:k+20]!r})")
        else:
            note = "  (tokens が返らない: return_tokens 非対応ビルド)"

        n1, n4 = indent_stats(content)
        print(f"  #{i:<3} {v:<10} [1sp={n1} 4sp={n4}] tokens={len(tokens)}{note}")
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
        for (t, pc), n in sorted(ws_tally.items(), key=lambda kv: -kv[1]):
            print(f"    {t:>7}  {pc!r:<12} x{n}")
    if indent_mismatches:
        print(f"  ⚠ インデント統計の不一致 {indent_mismatches}/{total} 回"
              " → デトークナイズ/集約側 (H2) を疑う")
    elif collapsed:
        print("  → トークンIDの段階で既に単一スペース。デトークナイズ側ではなく"
              " モデルがそのトークンを選んでいる。量子化・プロンプト非依存なら"
              " モデルの学習された挙動 (docs/INDENT_COLLAPSE.md 参照)")
    if other_mismatches:
        print(f"  (参考) 空白以外の差が {other_mismatches}/{total} 回。"
              " 特殊トークン (<think> 等) の表示差なら無視してよい")
    return 1 if collapsed else 0


def self_test() -> int:
    cases = [
        ("def f():\n    if x:\n        return 1\n", "ok"),
        ("def f():\n if x:\n return 1\n", "COLLAPSED"),
        ("def f():\n    if x:\n return 1\n", "MIXED"),
        ("x = 1\n", "ok"),
    ]
    bad = 0
    for text, want in cases:
        got = verdict_for(text)
        ok = got == want
        bad += not ok
        print(f"  {'✅' if ok else '❌'} want={want:<10} got={got}")
    print("  self-test:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8085")
    ap.add_argument("-n", type=int, default=10, help="試行回数 (既定10)")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--n-predict", type=int, default=512)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--show", type=int, default=0, metavar="N",
                    help="潰れた回の content を先頭N行だけ表示")
    ap.add_argument("--self-test", action="store_true", help="サーバ不要の内部テスト")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        return run_probe(args)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"ERROR: llama-server に到達できない ({args.url}): {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
