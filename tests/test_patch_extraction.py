"""patch.py 抽出器の回帰テスト.

ゴールデン入力は実測ラン (/tmp/q2 の artifacts) から該当箇所だけを抜き出した
最小再現入力 (tests/fixtures/*.txt)。以下の事故が二度と起きないことを固定する:

  * 同一パスのマーカーが複数あるときの**後勝ち上書き** (1,396B の実装が
    4B の `...` に潰される)
  * 出力フォーマットの雛形 (`<entire corrected file content>` / `<content>`)
    をコードとして採用してしまう
  * 散文が混ざって構文が壊れた巨大ブロックを「最長だから」で採用する
  * 逆に、思考中のドラフトから正しく救出できていたケースを壊す (退行)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from llmbench.patch import (
    ParsedPatch,
    _is_real_code,
    _norm,
    apply_patch,
    parse_llm_output,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def only_code(patch: ParsedPatch, path: str) -> str:
    assert patch.parse_ok, f"parse_ok=False ({patch.error})"
    assert list(patch.files) == [path]
    return patch.files[path]


# ────────────────── _is_real_code の単体 ──────────────────

@pytest.mark.parametrize("code", [
    "",
    "   \n  ",
    "...",
    "\n...\n",
    "pass",
    "<entire corrected file content>",
    "<content>",
    "<relative/path.py>",
    "def f():\n    ...\n",              # 雛形だけの関数
    "class C:\n    pass\n",             # 雛形だけのクラス
    '"""module docstring only"""\n',    # docstringだけ
    "def f(:\n  return 1\n",            # SyntaxError
])
def test_is_real_code_rejects_non_implementations(code):
    assert _is_real_code(code, "x.py") is False


@pytest.mark.parametrize("code", [
    "x = 1\n",
    "import os\n\n\ndef f():\n    return os.sep\n",
    "def f():\n    '''doc'''\n    return 1\n",
    "class C:\n    def m(self):\n        return 2\n",
])
def test_is_real_code_accepts_implementations(code):
    assert _is_real_code(code, "x.py") is True


def test_is_real_code_skips_syntax_check_for_non_python():
    """.py 以外 (JS/MD等) に ast を課すと正しい出力まで捨ててしまう."""
    js = "function f() { return 1; }\n"
    assert _is_real_code(js, "app.js") is True
    assert _is_real_code(js, "app.py") is False
    assert _is_real_code("<content>", "app.js") is False


# ────────────────── ① 後勝ち上書き (t057) ──────────────────

def test_duplicate_marker_keeps_real_implementation_not_ellipsis():
    """437行目の1,396B実装が、561行目の4B `...` に潰されないこと."""
    text = load("t057_duplicate_marker.txt")
    patch = parse_llm_output(text, ["sniff.py"])
    code = only_code(patch, "sniff.py")
    assert len(code) > 1000, f"実装ではなく {len(code)}B のものを拾っている"
    assert code.strip() != "..."
    tree = ast.parse(code)
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"sniff_delimiter", "parse"} <= names, names


# ────────────────── ② テンプレ復唱 (t095) ──────────────────

def test_template_echo_is_not_adopted():
    text = load("t095_template_echo.txt")
    patch = parse_llm_output(text, ["labelcheck.py"])
    code = only_code(patch, "labelcheck.py")
    assert "<entire corrected file content>" not in code
    assert _is_real_code(code, "labelcheck.py")


# ────────────────── ③ プレースホルダ (t064) ──────────────────

def test_placeholder_content_is_not_adopted():
    text = load("t064_placeholder.txt")
    patch = parse_llm_output(text, ["allocate.py"])
    code = only_code(patch, "allocate.py")
    assert code.strip() != "<content>"
    assert "def allocate" in code


def test_placeholder_path_gives_actionable_error():
    """`--- FILE: <relative/path.py> ---` は雛形の復唱だと分かる文言で落とす."""
    text = (
        "--- FILE: <relative/path.py> ---\n"
        "```python\n"
        "x = 1\n"
        "```\n"
    )
    patch = parse_llm_output(text, ["real.py"])
    assert patch.parse_ok is False
    assert "プレースホルダ" in patch.error


# ────────────────── ④ 散文混入 (t093) ──────────────────

def test_prose_contaminated_block_is_rejected():
    """構文が壊れている巨大ブロックを「最長だから」で採用しないこと."""
    text = load("t093_prose_contaminated.txt")
    patch = parse_llm_output(text, ["canonpath.py"])
    assert patch.parse_ok is False
    assert not patch.files
    assert patch.error


# ────────────────── ⑤ 退行防止 ──────────────────

def test_rescue_from_reasoning_still_works():
    """上限到達ランで思考中のドラフトを拾えていたケース (9/9合格) を壊さない."""
    text = load("t093_rescue_from_reasoning.txt")
    patch = parse_llm_output(text, ["canonpath.py"])
    code = only_code(patch, "canonpath.py")
    assert "def resolve_subpath" in code
    assert len(code) == 831


def test_normal_output_unchanged():
    """上限未到達の通常タスクは従来と同一の抽出結果になること."""
    text = load("t060_normal.txt")
    patch = parse_llm_output(text, ["ueq.py"])
    code = only_code(patch, "ueq.py")
    assert code.startswith("import unicodedata")
    assert "def equal(a, b, fold=False):" in code
    assert code.rstrip().endswith("return a == b")


# ────────────────── 段階2/3 と正規化 ──────────────────

def test_inline_path_form_requires_real_code():
    text = (
        "まず雛形:\n```python:a.py\n...\n```\n"
        "本番:\n```python:a.py\ndef f():\n    return 1\n```\n"
    )
    patch = parse_llm_output(text, ["a.py"])
    assert only_code(patch, "a.py").strip() == "def f():\n    return 1"


def test_single_file_fallback_prefers_whole_module_over_fragment():
    """マーカーが無いとき、末尾の断片ではなく完全なモジュールを拾う."""
    text = (
        "考える。\n```\nimport os\n\n\ndef f():\n    return os.sep\n\n\n"
        "def g():\n    return 2\n```\n"
        "この部分だけ直す:\n```\nreturn os.sep\n```\n"
    )
    patch = parse_llm_output(text, ["m.py"])
    code = only_code(patch, "m.py")
    assert "def f()" in code and "def g()" in code


def test_non_python_fence_tags_do_not_shift_block_pairing():
    """```json ブロックを1つのブロックとして消費し、フェンス対応をずらさない."""
    text = (
        "--- FILE: a.py ---\n"
        "```json\n"
        '{"note": "これはコードではない"}\n'
        "```\n"
        "```python\n"
        "def f():\n    return 1\n"
        "```\n"
    )
    patch = parse_llm_output(text, ["a.py"])
    assert only_code(patch, "a.py").strip() == "def f():\n    return 1"


def test_norm_does_not_turn_parent_traversal_into_known_file():
    """lstrip('./') は文字集合の除去なので ../foo.py が foo.py に化けていた."""
    assert _norm("../foo.py") == "../foo.py"
    assert _norm("./foo.py") == "foo.py"
    assert _norm("././foo.py") == "foo.py"
    assert _norm("/foo.py") == "foo.py"
    assert _norm("`foo.py`") == "foo.py"
    text = "--- FILE: ../foo.py ---\n```python\nx = 1\n```\n"
    patch = parse_llm_output(text, ["foo.py"])
    assert patch.parse_ok is False
    assert "unknown/unsafe" in patch.error


# ────────────────── error / parse_ok の整合 ──────────────────

def test_partial_rejection_keeps_parse_ok_without_error():
    """一部パス拒否で parse_ok=True と error 非空が両立しないこと."""
    text = (
        "--- FILE: good.py ---\n```python\nx = 1\n```\n"
        "--- FILE: /etc/passwd ---\n```python\ny = 2\n```\n"
    )
    patch = parse_llm_output(text, ["good.py"])
    assert patch.parse_ok is True
    assert patch.error == ""
    assert patch.warnings and "etc/passwd" in patch.warnings[0]
    assert patch.suspect is True
    assert list(patch.files) == ["good.py"]


def test_all_rejected_sets_error_and_parse_ng():
    text = "--- FILE: /etc/passwd ---\n```python\ny = 2\n```\n"
    patch = parse_llm_output(text, ["good.py"])
    assert patch.parse_ok is False
    assert "unknown/unsafe" in patch.error
    assert patch.suspect is True


def test_empty_output():
    patch = parse_llm_output("   ", ["a.py"])
    assert patch.parse_ok is False and patch.error == "empty output"
    assert not patch.warnings


def test_apply_patch_roundtrip(tmp_path):
    patch = parse_llm_output(load("t060_normal.txt"), ["ueq.py"])
    written = apply_patch(patch, tmp_path)
    assert written == ["ueq.py"]
    text = (tmp_path / "ueq.py").read_text(encoding="utf-8")
    assert text.endswith("\n")
    ast.parse(text)
