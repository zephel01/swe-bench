"""usabilityティア分類.

ベンチのスコアを「実際どれくらい任せられるか」という運用判断に翻訳する。
信頼性 (success_rate) と品質 (quality) の2軸でタスクを3ティアに分類する:

- autonomous (🟢 自律)  … レビューほぼ不要で任せられる
- assisted   (🟡 補助)  … レビュー前提なら使える
- unusable   (🔴 不可)  … この種のタスクには任せられない

しきい値は config.yaml の `usability:` で上書きできる。
"""

from __future__ import annotations

from collections import Counter

TIERS = ("autonomous", "assisted", "unusable")

TIER_LABEL = {
    "autonomous": "🟢 自律",
    "assisted": "🟡 補助",
    "unusable": "🔴 不可",
}

TIER_DESC = {
    "autonomous": "レビューほぼ不要で任せられる",
    "assisted": "レビュー前提なら使える",
    "unusable": "この種のタスクには任せられない",
}

DEFAULTS = {
    "autonomous": {"min_success": 0.9, "min_quality": 80.0},
    "assisted": {"min_success": 0.6, "min_quality": 0.0},
}


def classify(success_rate: float, quality: float, cfg: dict | None = None) -> str:
    """(success_rate, quality) をティアに分類する."""
    cfg = cfg or {}
    auto = {**DEFAULTS["autonomous"], **(cfg.get("autonomous") or {})}
    assist = {**DEFAULTS["assisted"], **(cfg.get("assisted") or {})}
    if success_rate >= auto["min_success"] and quality >= auto["min_quality"]:
        return "autonomous"
    if success_rate >= assist["min_success"] and quality >= assist["min_quality"]:
        return "assisted"
    return "unusable"


def aggregate(results, cfg: dict | None = None):
    """tier別カウントと、難易度×tierのマトリクスを返す.

    戻り値: (overall: Counter, by_difficulty: dict[str, Counter])
    """
    overall: Counter = Counter()
    by_diff: dict[str, Counter] = {}
    for r in results:
        tier = getattr(r, "usability_tier", "") or classify(
            r.success_rate, r.quality_score, cfg
        )
        overall[tier] += 1
        by_diff.setdefault(r.difficulty, Counter())[tier] += 1
    return overall, by_diff
