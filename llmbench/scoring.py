"""複合スコア計算.

combined = resolved * (floor + (1 - floor) * quality / 100) * 100

resolved=0 → 0点 (動かないコードは品質に関わらず0)
resolved=1 → floor*100 〜 100点 (品質で差別化)
"""

from __future__ import annotations


def combined_score(resolved: bool, quality: float, scoring_cfg: dict) -> float:
    floor = float(scoring_cfg.get("quality_floor", 0.5))
    if not resolved:
        return 0.0
    q = max(0.0, min(100.0, quality))
    return round((floor + (1.0 - floor) * q / 100.0) * 100.0, 1)
