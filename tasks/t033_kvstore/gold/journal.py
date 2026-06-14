"""ネストしたトランザクション用の undo ジャーナル (レイヤースタック)."""

from __future__ import annotations

MISSING = object()  # キーが存在しなかったことを表す番兵


class Journal:
    def __init__(self) -> None:
        self._layers: list[dict] = []

    def depth(self) -> int:
        return len(self._layers)

    def begin(self) -> None:
        self._layers.append({})

    def record(self, key, old_value) -> None:
        """変更前の値を現在レイヤーに1度だけ控える."""
        if self._layers and key not in self._layers[-1]:
            self._layers[-1][key] = old_value

    def commit(self) -> None:
        """現在レイヤーを解放し、未記録分を親レイヤーへ引き継ぐ."""
        if not self._layers:
            raise RuntimeError("no active transaction")
        inner = self._layers.pop()
        if self._layers:
            parent = self._layers[-1]
            for key, old in inner.items():
                if key not in parent:
                    parent[key] = old

    def rollback(self) -> dict:
        """現在レイヤーの undo 情報を返してレイヤーを破棄する."""
        if not self._layers:
            raise RuntimeError("no active transaction")
        return self._layers.pop()
