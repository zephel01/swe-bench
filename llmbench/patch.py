"""LLM出力のパースとファイル適用.

出力フォーマット (プロンプトで指示する正規形式):

    --- FILE: relative/path.py ---
    ```python
    <ファイル全体の修正後コード>
    ```

ローカルLLMはunified diffの行番号を正確に出せないことが多いため、
v1では「ファイル全体置換」方式を採用する。
フォールバックとして ```python:path``` 形式と、単一コードブロックも解釈する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

FILE_MARKER_RE = re.compile(
    r"^[-*\s]*FILE:\s*(?P<path>\S+?)\s*[-*\s]*$", re.MULTILINE
)
CODE_BLOCK_RE = re.compile(
    r"```(?:python|py)?(?::(?P<inline_path>\S+))?\s*\n(?P<code>.*?)```",
    re.DOTALL,
)

# harmony/channel系モデルの制御トークン (例: <|channel>, <channel|>, <|message|>)。
# 「< と > の間にパイプ | を含むタグ」だけを除去する。通常のHTML/XMLタグ
# (<li>, <ul>, <script> 等＝フロント系モデルがコード中に出す) はパイプを含まない
# ので保持される。
CONTROL_TOKEN_RE = re.compile(r"<\|[^<>]*>|<[^<>]*\|>")


def _strip_control_tokens(text: str) -> str:
    return CONTROL_TOKEN_RE.sub("", text)


@dataclass
class ParsedPatch:
    """パース済みpatch: 相対パス -> 修正後ファイル内容."""

    files: dict[str, str] = field(default_factory=dict)
    parse_ok: bool = False
    error: str = ""


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
    markers = list(FILE_MARKER_RE.finditer(text))
    for i, m in enumerate(markers):
        seg_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        segment = text[m.end():seg_end]
        block = CODE_BLOCK_RE.search(segment)
        if block:
            patch.files[_norm(m.group("path"))] = block.group("code")

    # 2. ```python:path``` 形式
    if not patch.files:
        for block in CODE_BLOCK_RE.finditer(text):
            p = block.group("inline_path")
            if p:
                patch.files[_norm(p)] = block.group("code")

    # 3. フォールバック: 単一ファイルタスクなら最大のコードブロックを充てる
    if not patch.files and len(known_files) == 1:
        blocks = [b.group("code") for b in CODE_BLOCK_RE.finditer(text)]
        candidates = [b for b in blocks if _looks_like_python(b)]
        if candidates:
            patch.files[known_files[0]] = max(candidates, key=len)

    if not patch.files:
        patch.error = "no file blocks found in output"
        return patch

    # パス検証: 既知ファイル以外への書込みは拒否 (path traversal対策込み)
    known = set(known_files)
    bad = [p for p in patch.files if p not in known or ".." in Path(p).parts]
    if bad:
        patch.error = f"unknown/unsafe paths: {bad}"
        patch.files = {p: c for p, c in patch.files.items() if p not in bad}
        if not patch.files:
            return patch

    patch.parse_ok = True
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
    return p.strip().strip("`'\"").replace("\\", "/").lstrip("./")


def _looks_like_python(code: str) -> bool:
    hints = ("def ", "class ", "import ", "return", "=")
    return any(h in code for h in hints)
