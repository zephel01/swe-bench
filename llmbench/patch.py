"""LLM出力のパースとファイル適用.

出力フォーマット (プロンプトで指示する正規形式):

    --- FILE: relative/path.py ---
    ```python
    <ファイル全体の修正後コード>
    ```

ローカルLLMはunified diffの行番号を正確に出せないことが多いため、
v1では「ファイル全体置換」方式を採用する。
フォールバックとして ```python:path``` 形式と、単一コードブロックも解釈する。

抽出は「先勝ち + 実コード判定」で行う:

  思考(thinking)を含む出力では、同じパスに対して複数のコードブロックが
  現れる。旧実装は**後勝ちで無条件上書き**していたため、思考中に書いた
  完全な実装 (1,396B) を、直後の「出力フォーマットの復唱」に含まれる
  ``...`` (4B) が上書きして潰す事故が実測で起きていた。
  そこで ``_is_real_code()`` を通ったブロックだけを候補とし、最初に
  見つかった実コードを採用する (``setdefault`` = 先勝ち)。
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

FILE_MARKER_RE = re.compile(
    r"^[-*\s]*FILE:\s*(?P<path>\S+?)\s*[-*\s]*$", re.MULTILINE
)
# フェンスは行頭アンカー付きで、言語タグは一般化する。
#   旧実装は ```(?:python|py)? しか受け付けず、```json / ```text / ```diff の
#   **開きフェンスに一致できない**ため、そのブロックの閉じフェンスを「開き」と
#   誤認してフェンス対応が1つずつズレていた (散文をコードとして拾う原因)。
CODE_BLOCK_RE = re.compile(
    r"^[ \t]*```[ \t]*(?P<lang>[A-Za-z0-9_+.-]*)(?::(?P<inline_path>\S+))?[ \t]*\n"
    r"(?P<code>.*?)"
    r"^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)

# harmony/channel系モデルの制御トークン (例: <|channel>, <channel|>, <|message|>)。
# 「< と > の間にパイプ | を含むタグ」だけを除去する。通常のHTML/XMLタグ
# (<li>, <ul>, <script> 等＝フロント系モデルがコード中に出す) はパイプを含まない
# ので保持される。
CONTROL_TOKEN_RE = re.compile(r"<\|[^<>]*>|<[^<>]*\|>")

# `<entire corrected file content>` / `<content>` / `<relative/path.py>` のような、
# プロンプトの雛形をそのまま復唱しただけのプレースホルダ。
PLACEHOLDER_RE = re.compile(r"^<[^<>\n]{0,200}>$")

# ast で構文が通る拡張子 (それ以外は構文チェックを課さない)
_PY_SUFFIXES = (".py", ".pyi")

# Pythonコードとして採用してよいフェンスの言語タグ。
# ```json / ```text / ```diff のように**明示的に別言語だと宣言された**ブロックは
# 採用しない (JSONオブジェクトは dict リテラルとして ast.parse を通ってしまう)。
_PY_LANG_TAGS = frozenset({"", "python", "py", "python3", "py3", "python2"})


def _strip_control_tokens(text: str) -> str:
    return CONTROL_TOKEN_RE.sub("", text)


@dataclass
class ParsedPatch:
    """パース済みpatch: 相対パス -> 修正後ファイル内容."""

    files: dict[str, str] = field(default_factory=dict)
    parse_ok: bool = False
    error: str = ""
    # 抽出はできたが疑わしい点 (一部パス拒否など)。parse_ok=True でも入りうる。
    # error は「抽出できなかった理由」だけに使い、両立しない状態を作らない。
    warnings: list[str] = field(default_factory=list)

    @property
    def suspect(self) -> bool:
        """抽出結果を鵜呑みにできない (再生成を検討すべき) か."""
        return bool(self.error or self.warnings)


def _is_placeholder(s: str) -> bool:
    """`<entire corrected file content>` 等の雛形プレースホルダか."""
    return bool(PLACEHOLDER_RE.match(s.strip()))


def _is_stub_node(node: ast.AST) -> bool:
    """`pass` / `...` / docstring / 裸のリテラルだけの「中身の無い」ノードか.

    裸のリテラルを含めるのは、```json ブロックの ``{"a": 1}`` が Python の
    dict リテラルとして ast.parse を通ってしまうため (ファイル置換の中身
    としては明らかに誤り)。
    """
    if isinstance(node, ast.Pass):
        return True
    if isinstance(node, ast.Expr):
        try:
            ast.literal_eval(node.value)     # 定数・dict/list/tuple リテラル
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return all(_is_stub_node(child) for child in node.body)
    return False


def _is_real_code(code: str, path: str | None = None) -> bool:
    """「実際に適用する価値のあるコード」かを判定する.

    True になる条件:
      * 空でない
      * `<...>` 形式のプレースホルダ単体でない
      * ``ast.parse`` が通る (Pythonファイル対象のときのみ)
      * body が空でない
      * ``...`` (Ellipsis) / ``pass`` / docstring だけの雛形でない

    path が Python 以外 (.js/.md 等) を指す場合は構文チェックを課さず、
    「空でない & プレースホルダでない」だけを見る (誤検知で捨てないため)。
    """
    if not code or not code.strip():
        return False
    stripped = code.strip()
    if _is_placeholder(stripped):
        return False
    if path is not None and not str(path).lower().endswith(_PY_SUFFIXES):
        return True
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    if not tree.body:
        return False
    return not all(_is_stub_node(node) for node in tree.body)


def _accept_block(block: re.Match[str], path: str | None) -> str | None:
    """コードブロックを採用してよければその中身を、駄目なら None を返す."""
    lang = (block.group("lang") or "").lower()
    is_py = path is None or str(path).lower().endswith(_PY_SUFFIXES)
    if is_py and lang not in _PY_LANG_TAGS:
        return None                       # ```json / ```text 等は採用しない
    code = block.group("code")
    return code if _is_real_code(code, path) else None


def _looks_like_whole_module(code: str, path: str | None = None) -> bool:
    """「ファイル全体」に見えるブロックか (断片ではないか).

    段階3のフォールバックでは、思考中に貼られた数行の断片ではなく
    「そのまま1ファイルとして成立するブロック」を優先したい。
    先頭行がインデントされておらず、トップレベルに import / def / class が
    あるものを「モジュール全体」とみなす。
    """
    if not _is_real_code(code, path):
        return False
    first = next((ln for ln in code.splitlines() if ln.strip()), "")
    if first[:1] in (" ", "\t"):
        return False
    if path is not None and not str(path).lower().endswith(_PY_SUFFIXES):
        return True
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                       ast.Import, ast.ImportFrom))
        for n in tree.body
    )


def parse_llm_output(text: str, known_files: list[str]) -> ParsedPatch:
    """LLM出力からファイル置換patchを抽出する.

    known_files: タスクのbuggy_code配下の相対パス一覧 (パス検証と
    単一ファイルタスクのフォールバックに使用)
    """
    patch = ParsedPatch()
    if not text or not text.strip():
        patch.error = "empty output"
        return patch

    # harmony/channel系モデル (例: <|channel>thought<channel|>) の制御トークンを
    # 除去してから抽出する。これらが FILE マーカー行に前置されると抽出に失敗するため。
    text = _strip_control_tokens(text)

    # 1. 正規形式: --- FILE: path --- の直後のコードブロック
    #    同じパスが複数回現れても**先に見つかった実コードを残す** (setdefault)。
    markers = list(FILE_MARKER_RE.finditer(text))
    for i, m in enumerate(markers):
        seg_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        segment = text[m.end():seg_end]
        path = _norm(m.group("path"))
        if path in patch.files:          # 先勝ち: 既に実コードを確保済み
            continue
        for block in CODE_BLOCK_RE.finditer(segment):
            code = _accept_block(block, path)
            if code is not None:
                patch.files.setdefault(path, code)
                break

    # 2. ```python:path``` 形式 (こちらも先勝ち + 実コードのみ)
    if not patch.files:
        for block in CODE_BLOCK_RE.finditer(text):
            p = block.group("inline_path")
            if not p:
                continue
            path = _norm(p)
            if path in patch.files:
                continue
            code = _accept_block(block, path)
            if code is not None:
                patch.files.setdefault(path, code)

    # 3. フォールバック: 単一ファイルタスクなら、_is_real_code を通ったブロックから選ぶ。
    #    旧実装は「`=` を含めばPython」(_looks_like_python) という緩すぎる判定で
    #    最長ブロックを採っていたため、散文が混ざって構文エラーになる巨大ブロック
    #    (実測 24,048B) を平然と採用していた。判定を _is_real_code に置き換え、
    #    さらに「モジュール全体に見える」ブロックを優先する。
    if not patch.files and len(known_files) == 1:
        target = known_files[0]
        candidates = [
            code for code in (
                _accept_block(b, target) for b in CODE_BLOCK_RE.finditer(text)
            ) if code is not None
        ]
        pool = [c for c in candidates if _looks_like_whole_module(c, target)]
        pool = pool or candidates
        best = ""
        for code in pool:                       # 同点なら後勝ち (後の版が新しい)
            if len(code) >= len(best):
                best = code
        if best:
            patch.files[target] = best

    if not patch.files:
        patch.error = "no file blocks found in output"
        return patch

    # パス検証: 既知ファイル以外への書込みは拒否 (path traversal対策込み)
    known = set(known_files)
    bad = [p for p in patch.files if p not in known or ".." in Path(p).parts]
    if bad:
        msg = f"unknown/unsafe paths: {bad}"
        placeholders = [p for p in bad if _is_placeholder(p)]
        if placeholders:
            msg += (
                f" — パスがプレースホルダのままです {placeholders}。"
                "モデルが出力フォーマットの雛形を復唱しただけで、"
                "実際の修正ファイルを出力していない可能性が高いです"
            )
        patch.files = {p: c for p, c in patch.files.items() if p not in bad}
        if not patch.files:
            # 何も残らない = 抽出失敗。error にだけ入れる。
            patch.error = msg
            return patch
        # 一部は有効。parse_ok=True と error 非空が両立する矛盾を避けるため、
        # 残った分は採用しつつ理由は warnings 側に置く。
        patch.warnings.append(msg)

    patch.parse_ok = True
    patch.error = ""
    return patch


def apply_patch(patch: ParsedPatch, target_dir: Path) -> list[str]:
    """patchをtarget_dirに書き込み、変更したファイルの相対パスを返す."""
    written = []
    for rel, content in patch.files.items():
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not content.endswith("\n"):
            content += "\n"
        dest.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


def _norm(p: str) -> str:
    """パス表記を正規化する.

    注: 旧実装は ``lstrip("./")`` を使っていたが、これは**文字集合**の除去
    なので ``../foo.py`` が ``foo.py`` になり、traversal 表記が静かに
    「既知ファイル」に化けていた。前置の ``./`` だけを落とす。
    """
    p = p.strip().strip("`'\"").replace("\\", "/")
    p = re.sub(r"^(?:\./)+", "", p)
    return p.lstrip("/")
