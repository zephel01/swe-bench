"""依存性注入コンテナ。singletonライフサイクルと循環依存検出."""

from __future__ import annotations


class Container:
    def __init__(self) -> None:
        self._factories: dict = {}
        self._singleton: dict[str, bool] = {}
        self._instances: dict = {}
        self._resolving: set = set()

    def register(self, name: str, factory, singleton: bool = False) -> None:
        self._factories[name] = factory
        self._singleton[name] = singleton

    def resolve(self, name: str):
        if name not in self._factories:
            raise KeyError(f"not registered: {name}")
        if self._singleton[name] and name in self._instances:
            return self._instances[name]
        if name in self._resolving:
            raise ValueError(f"cyclic dependency: {name}")
        self._resolving.add(name)
        try:
            instance = self._factories[name](self)
        finally:
            self._resolving.discard(name)
        if self._singleton[name]:
            self._instances[name] = instance
        return instance
