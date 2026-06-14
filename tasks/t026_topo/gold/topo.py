"""トポロジカルソート (Kahn法)。辞書順で安定、循環はValueError."""

from __future__ import annotations

import heapq


def toposort(graph: dict) -> list:
    nodes = set(graph)
    for succ in graph.values():
        nodes.update(succ)
    indeg = dict.fromkeys(nodes, 0)
    adj: dict = {n: [] for n in nodes}
    for u in graph:
        for v in graph[u]:
            adj[u].append(v)
            indeg[v] += 1

    heap = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(heap)
    order: list = []
    while heap:
        n = heapq.heappop(heap)
        order.append(n)
        for v in adj[n]:
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(heap, v)

    if len(order) != len(nodes):
        raise ValueError("graph has a cycle")
    return order
