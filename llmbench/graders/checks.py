"""制約チェック評価器 (IFEval 方式).

constraint grader と judge grader の hard_constraints で共用する。
各チェックはプログラムで決定的に検証可能。テキスト (モデルの回答) に対して
チェック配列を実行し、通過/不通過のリストを返す。

カウント規約 (タスク作成者と grader で一致させること):
  - word_count : len(text.split())            … 空白区切りの語数
  - line_count : 非空行の数                     … [l for l in splitlines() if l.strip()]
  - char_count : len(text.strip())
"""

from __future__ import annotations

import json
import re

from ..patch import _strip_control_tokens

_ANSWER_MARKER_RE = re.compile(r"-{2,}\s*ANSWER\s*-{2,}", re.I)


def extract_answer(text: str) -> str:
    """`--- ANSWER ---` マーカー以降を回答本文として取り出す.

    マーカーが無ければ全文を回答とみなす。制御トークン (harmony系) は除去する。
    """
    text = _strip_control_tokens(text or "")
    parts = _ANSWER_MARKER_RE.split(text)
    ans = parts[-1] if len(parts) > 1 else text
    return ans.strip()


def _words(text: str) -> int:
    return len(text.split())


def _lines(text: str) -> int:
    return len([ln for ln in text.splitlines() if ln.strip()])


def _get_path(obj, path: str):
    """ドット区切りパスで JSON を辿る (list は数値インデックス)."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(part)
    return cur


def _eval_one(text: str, chk: dict) -> tuple[bool, str]:
    kind = chk.get("kind")
    ci = chk.get("ci", False)
    hay = text.lower() if ci else text

    if kind == "word_count":
        n = _words(text)
        lo, hi = chk.get("min"), chk.get("max")
        ok = (lo is None or n >= lo) and (hi is None or n <= hi)
        return ok, f"{n}語 (min={lo} max={hi})"
    if kind == "line_count":
        n = _lines(text)
        lo, hi = chk.get("min"), chk.get("max")
        ok = (lo is None or n >= lo) and (hi is None or n <= hi)
        return ok, f"{n}行 (min={lo} max={hi})"
    if kind == "char_count":
        n = len(text.strip())
        lo, hi = chk.get("min"), chk.get("max")
        ok = (lo is None or n >= lo) and (hi is None or n <= hi)
        return ok, f"{n}字 (min={lo} max={hi})"
    if kind == "contains":
        t = chk["text"]
        needle = t.lower() if ci else t
        return needle in hay, f"contains {t!r}"
    if kind == "not_contains":
        t = chk["text"]
        needle = t.lower() if ci else t
        return needle not in hay, f"not_contains {t!r}"
    if kind == "starts_with":
        t = chk["text"]
        return (hay.lstrip().startswith(t.lower() if ci else t)), f"starts_with {t!r}"
    if kind == "ends_with":
        t = chk["text"]
        return (hay.rstrip().endswith(t.lower() if ci else t)), f"ends_with {t!r}"
    if kind == "equals":
        t = chk["text"]
        a = text.strip().lower() if ci else text.strip()
        b = t.lower() if ci else t
        return a == b, f"equals {t!r}"
    if kind == "regex":
        flags = 0
        for f in chk.get("flags", ""):
            flags |= {"i": re.I, "m": re.M, "s": re.S}.get(f, 0)
        found = re.search(chk["pattern"], text, flags) is not None
        ok = (not found) if chk.get("negate") else found
        return ok, f"regex {chk['pattern']!r}{' (negate)' if chk.get('negate') else ''}"
    if kind == "json_valid":
        try:
            json.loads(text.strip())
            return True, "json_valid"
        except Exception as e:
            return False, f"json invalid: {e}"
    if kind == "json_path":
        try:
            obj = json.loads(text.strip())
            val = _get_path(obj, chk["path"])
        except Exception as e:
            return False, f"json_path {chk.get('path')!r}: {e}"
        if "equals" in chk:
            return val == chk["equals"], f"json_path {chk['path']}={val!r} (==({chk['equals']!r}))"
        return True, f"json_path {chk['path']} exists"
    return False, f"未知のcheck kind: {kind}"


def run_checks(text: str, checks: list[dict]) -> list[dict]:
    """チェック配列を実行し [{kind, desc, passed, detail}] を返す."""
    out = []
    for chk in checks:
        try:
            ok, detail = _eval_one(text, chk)
        except Exception as e:  # チェック定義不備は不通過扱い (全体は落とさない)
            ok, detail = False, f"check error: {e}"
        out.append({
            "kind": chk.get("kind"),
            "desc": chk.get("desc", ""),
            "passed": bool(ok),
            "detail": detail,
        })
    return out
