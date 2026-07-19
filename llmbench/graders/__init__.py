"""Pluggable grader フレームワーク.

各 grader は「出力契約 (プロンプト)」と「採点」を所有し、最終的に
(resolved: bool, quality_score: 0-100) という共通インターフェイスに正規化して返す。
これにより runner の集計 (_aggregate_attempts) / combined_score / pass@k /
usability / certify を一切変更せず再利用できる。

詳細は DESIGN_DOMAINS.md を参照。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GradeCtx:
    """grader.evaluate に渡す実行コンテキスト."""

    work_root: Path
    quality_cfg: dict = field(default_factory=dict)
    scoring_cfg: dict = field(default_factory=dict)
    graders_cfg: dict = field(default_factory=dict)   # config の graders:
    reviewer: object = None                           # code grader の LLMレビュー用
    judge: object = None                              # judge grader の採点モデル
    judge_seeds: int = 1
    timeout: int = 120
    lang: str = "en"


@dataclass
class GraderEval:
    """採点結果 (Attempt に写像される正規化済みフィールド)."""

    resolved: bool = False
    quality_score: float = 0.0
    parse_ok: bool = False
    parse_error: str = ""
    parsed_files: dict = field(default_factory=dict)   # artifacts 保存物
    fail_reason: str = ""
    components: dict = field(default_factory=dict)      # 採点内訳 (レポート表示)
    detail_output: str = ""                             # 採点詳細 (test_output 相当)


class Grader(ABC):
    name: str = "base"
    domain: str = "code"

    @abstractmethod
    def build_prompt(self, task, lang: str) -> tuple[str, str]:
        """(system, user) プロンプトを返す (出力フォーマットの指示を含む)."""

    @abstractmethod
    def evaluate(self, task, raw_output: str, ctx: GradeCtx) -> GraderEval:
        """モデル出力を採点して GraderEval を返す."""

    # --- validate (MockClient) 用 ---
    def mock_gold(self, task) -> str:
        """正解相当の出力 (resolved になるべき)."""
        raise NotImplementedError

    def mock_broken(self, task) -> str:
        """失敗すべき出力 (resolved にならないべき)."""
        return "raise SyntaxError(  # 壊れた出力 (フォーマット不正)"


# grader 名 -> インスタンス (遅延生成でモジュール循環を避ける)
_CACHE: dict[str, Grader] = {}


def get_grader(name: str | None) -> Grader:
    name = (name or "code").lower()
    if name in _CACHE:
        return _CACHE[name]
    if name == "code":
        from .code import CodeGrader
        g: Grader = CodeGrader()
    elif name == "detection":
        from .detection import DetectionGrader
        g = DetectionGrader()
    elif name == "constraint":
        from .constraint import ConstraintGrader
        g = ConstraintGrader()
    elif name == "judge":
        from .judge import JudgeGrader
        g = JudgeGrader()
    elif name == "qa":
        from .qa import QaGrader
        g = QaGrader()
    else:
        raise ValueError(
            f"未知の grader: {name!r} (code|detection|constraint|judge|qa のいずれか)"
        )
    _CACHE[name] = g
    return g


# grader 名 -> ドメイン (results 記録・certify 用)。台帳が domain を持たない場合の既定。
GRADER_DOMAIN = {
    "code": "code",
    "detection": "security",
    "constraint": "general",
    "judge": "writing",
    "qa": "medical",
}
