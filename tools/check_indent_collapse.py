#!/usr/bin/env python3
"""llmbench artifacts の「インデント潰れ」を検出する.

llama.cpp の投機デコード (--spec-type draft-mtp) を量子化ターゲットで使うと、
生成テキストの行頭空白が **深さに関係なく1スペース** に潰れることがある。
llmbench/patch.py の _is_real_code() は ast.parse() を通すため、潰れた出力は
IndentationError で棄却され、generated/ が空 = 採点前に無条件fail になる。
スコアだけを見ていると「モデルが解けなかった」と区別できないので、
ラン後にこれを回して COLLAPSED が 0 であることを確認する。

    python3 tools/check_indent_collapse.py <artifacts_dir> [...]

llm_output.txt (LLM生出力) だけを見るので results.json は不要。
判定は patch.py と同じ「先勝ち + 実コード判定」に合わせてあり、
思考中の断片ブロックが先に来ても誤検知しない。

判定値:
  ok                   … 採用できるコードブロックがあり、4スペース系
  COLLAPSED            … 行頭が1スペースのみ + 構文エラー (これが事故)
  COLLAPSED-but-parses … 行頭が1スペースのみだが平坦なので構文は通った
                         (潰れは起きている。ネストがあれば落ちていた)
  NO-PARSABLE-BLOCK    … python として通るブロックが1つも無い (潰れ以外の原因)
  NO-CODE-BLOCK        … コードフェンスが無い / 閉じていない
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# llmbench/patch.py の CODE_BLOCK_RE と同等 (行頭アンカー・言語タグ一般化)
CODE_BLOCK_RE = re.compile(
    r"^[ \t]*```[ \t]*(?P<lang>[A-Za-z0-9_+.-]*)(?::(?P<inline_path>\S+))?[ \t]*\n"
    r"(?P<code>.*?)"
    r"^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
# patch.py の _PY_LANG_TAGS と同じ
PY_LANG_TAGS = frozenset({"", "python", "py", "python3", "py3", "python2"})

INDENT_1SP = re.compile(r"^ [^ \t]")
INDENT_4SP = re.compile(r"^    [^ \t]")


def indent_stats(code: str) -> tuple[int, int]:
    lines = code.splitlines()
    return (
        sum(1 for ln in lines if INDENT_1SP.match(ln)),
        sum(1 for ln in lines if INDENT_4SP.match(ln)),
    )


def classify(text: str) -> tuple[str, str]:
    """(判定, 詳細) を返す. patch.py と同じ先勝ち方針で候補ブロックを選ぶ."""
    blocks = [
        m.group("code")
        for m in CODE_BLOCK_RE.finditer(text)
        if (m.group("lang") or "").lower() in PY_LANG_TAGS and m.group("code").strip()
    ]
    if not blocks:
        return "NO-CODE-BLOCK", "python として読めるコードフェンスが無い"

    first_err = ""
    for code in blocks:
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
            if not first_err:
                lineno = getattr(e, "lineno", None)
                msg = getattr(e, "msg", str(e))
                first_err = f"{type(e).__name__}: {msg}" + (
                    f" (line {lineno})" if lineno else ""
                )
            continue
        if not tree.body:
            continue
        n1, n4 = indent_stats(code)
        if n1 and not n4:
            return "COLLAPSED-but-parses", f"ok [1sp={n1} 4sp={n4}]"
        if n1 and n4:
            return "MIXED", f"ok [1sp={n1} 4sp={n4}]"
        return "ok", f"ok [1sp={n1} 4sp={n4}]"

    # 1つも採用できなかった: 最初のブロックの状態で原因を出し分ける
    n1, n4 = indent_stats(blocks[0])
    verdict = "COLLAPSED" if (n1 and not n4) else "NO-PARSABLE-BLOCK"
    return verdict, f"{first_err} [1sp={n1} 4sp={n4}]"


def scan(root: Path) -> dict[str, int]:
    tally: dict[str, int] = {}
    rows: list[tuple[str, str, str, str]] = []
    for tdir in sorted(p for p in root.iterdir() if p.is_dir()):
        raw = tdir / "llm_output.txt"
        if not raw.is_file():
            continue
        verdict, detail = classify(raw.read_text(encoding="utf-8", errors="replace"))
        has_gen = (tdir / "generated").is_dir()
        tally[verdict] = tally.get(verdict, 0) + 1
        if verdict != "ok" or not has_gen:
            rows.append((tdir.name, "gen" if has_gen else "NOGEN", verdict, detail))

    print(f"\n=== {root.name} ===")
    for name, gen, verdict, detail in rows:
        print(f"  {name}  {gen:<5} {verdict:<20} {detail}")
    if not rows:
        print("  異常なし")
    total = sum(tally.values())
    print(
        f"  ---- {total}件: "
        + ", ".join(f"{k}={v}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
    )
    collapsed = tally.get("COLLAPSED", 0) + tally.get("COLLAPSED-but-parses", 0)
    if collapsed:
        print(
            f"  ⚠ インデント潰れ {collapsed}/{total} ({collapsed / total:.1%})。"
            " 投機デコード (--spec-type draft-mtp) と量子化の組み合わせを疑うこと。"
            " docs/MTP_INDENT_COLLAPSE.md 参照"
        )
    return tally


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    worst = 0
    for arg in argv[1:]:
        p = Path(arg)
        if not p.is_dir():
            print(f"ERROR: ディレクトリでない: {p}", file=sys.stderr)
            return 2
        t = scan(p)
        if t.get("COLLAPSED") or t.get("COLLAPSED-but-parses"):
            worst = 1
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
