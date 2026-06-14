"""優先度つきイベントバス。配信中の購読解除に対応."""

from __future__ import annotations

from events import Subscription


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Subscription]] = {}
        self._next_id = 0

    def subscribe(self, event: str, handler, priority: int = 0) -> int:
        self._next_id += 1
        sub = Subscription(self._next_id, priority, handler)
        self._subs.setdefault(event, []).append(sub)
        return sub.sub_id

    def unsubscribe(self, sub_id: int) -> None:
        for subs in self._subs.values():
            subs[:] = [s for s in subs if s.sub_id != sub_id]

    def publish(self, event: str, payload=None) -> None:
        order = sorted(
            self._subs.get(event, []), key=lambda s: (-s.priority, s.sub_id)
        )
        for sub in order:
            sub.handler(payload)
