"""複合スコア計算と信頼性指標 (pass@k).

combined = success_frac * (floor + (1 - floor) * quality / 100) * 100

- success_frac=0 → 0点 (動かないコードは品質に関わらず0)
- success_frac=1 → floor*100 〜 100点 (品質で差別化)
- 0 < success_frac < 1 (複数試行) → 成功率で線形にスケールする
  (例: 60%成功・品質90 → 0.6 * 95 = 57点)。信頼性を点に反映する。

後方互換: 単一試行 (runs=1) では success_frac は 0/1 のみを取り、
従来の `combined = resolved * (...)` と完全に一致する。
"""

from __future__ import annotations

import math


def combined_score(resolved, quality: float, scoring_cfg: dict) -> float:
    """複合スコアを返す.

    resolved: bool (単一試行) または 0.0-1.0 の成功率 (複数試行)。
    """
    floor = float(scoring_cfg.get("quality_floor", 0.5))
    frac = 1.0 if resolved is True else 0.0 if resolved is False else float(resolved)
    frac = max(0.0, min(1.0, frac))
    if frac <= 0.0:
        return 0.0
    q = max(0.0, min(100.0, quality))
    return round((floor + (1.0 - floor) * q / 100.0) * frac * 100.0, 1)


def pass_at_k(n: int, c: int, k: int) -> float:
    """pass@k の不偏推定量 (Chen et al. 2021, "Evaluating LLMs Trained on Code").

    n: 生成サンプル数, c: 成功サンプル数, k: 許容試行回数。
    「k回試して少なくとも1回成功する確率」の不偏推定。
    """
    if k <= 0 or n <= 0:
        return 0.0
    if c <= 0:
        return 0.0
    if n - c < k:
        return 1.0
    # 1 - C(n-c, k) / C(n, k)
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)
