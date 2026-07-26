"""品質評価レイヤー: Ruff / radon / LLMレビュー / SonarQube(任意)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from .ruff_check import ruff_score
from .complexity import complexity_score
from .llm_review import llm_review_score
from .sonar import sonar_score

# weight<=0 の警告を出したレイヤー名 (プロセス内で1回だけ警告する)
_WARNED_ZERO_WEIGHT: set[str] = set()


@dataclass
class QualityResult:
    score: float                       # 0-100 (重み付き合成)
    components: dict = field(default_factory=dict)   # 各レイヤーの詳細


def evaluate_quality(
    workspace: Path,
    changed_files: list[str],
    quality_cfg: dict,
    issue_text: str = "",
    reviewer_client=None,
) -> QualityResult:
    """変更ファイルに対して有効な品質レイヤーを実行し合成スコアを返す.

    無効/失敗/weight<=0 のレイヤーは重みを除外して再正規化する
    (weight の合計を1に揃える必要はない)。

    `enabled: true` かつ `weight <= 0` のレイヤーは実行はされるが合成に寄与
    しない。components には score が残りレポートには出てしまうため、
    `weight_ignored: True` を立てて stderr に1回だけ警告する。
    """
    components: dict = {}
    weighted: list[tuple[float, float]] = []  # (score, weight)

    def add(name: str, cfg_key: str, fn):
        cfg = quality_cfg.get(cfg_key, {})
        if not cfg.get("enabled", False):
            components[name] = {"enabled": False}
            return
        try:
            score, detail = fn(cfg)
        except Exception as e:  # レイヤー単体の失敗で全体を落とさない
            components[name] = {"enabled": True, "error": str(e)}
            return
        if score is None:
            components[name] = {"enabled": True, "skipped": True, **detail}
            return
        w = float(cfg.get("weight", 0.0))
        components[name] = {"enabled": True, "score": round(score, 1), **detail}
        if w > 0:
            weighted.append((score, w))
            return
        # enabled なのに weight<=0 → 実行コストを払って結果を捨てている状態。
        components[name]["weight_ignored"] = True
        if name not in _WARNED_ZERO_WEIGHT:
            _WARNED_ZERO_WEIGHT.add(name)
            print(
                f"⚠️  quality.{cfg_key}: enabled: true ですが weight={w} のため"
                f" スコアに寄与しません (実行はされ、レポートには表示されます)。"
                f" quality.{cfg_key}.weight に正の値を設定してください。"
                f" 重みは有効レイヤーだけで自動再正規化されるので、"
                f" 合計を1に揃える必要はありません。",
                file=sys.stderr,
            )

    add("ruff", "ruff", lambda c: ruff_score(workspace, changed_files, c))
    add("complexity", "complexity",
        lambda c: complexity_score(workspace, changed_files, c))
    add("llm_review", "llm_review",
        lambda c: llm_review_score(workspace, changed_files, c,
                                   issue_text, reviewer_client))
    add("sonarqube", "sonarqube", lambda c: sonar_score(workspace, c))

    if not weighted:
        return QualityResult(score=0.0, components=components)
    total_w = sum(w for _, w in weighted)
    score = sum(s * w for s, w in weighted) / total_w
    return QualityResult(score=round(score, 1), components=components)
