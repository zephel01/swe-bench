"""禁止辺つき最短経路 (ダイクストラ)."""

from __future__ import annotations

import heapq
import math


def shortest_path(graph: dict, start, goal, forbidden=()) -> float | None:
    """start->goal の最短距離。到達不能なら None。

    forbidden は使用禁止の有向辺 (u, v) の集合。
    """
    banned = set(forbidden)
    dist = {start: 0}
    pq: list[tuple[float, object]] = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist.get(u, math.inf):
            continue
        for v, w in graph.get(u, {}).items():
            if (u, v) in banned:
                continue
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist.get(goal)
