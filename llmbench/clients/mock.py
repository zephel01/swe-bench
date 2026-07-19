"""検証用モッククライアント.

mode=gold   : タスクの grader が定める「正解相当」出力を返す (resolved になるべき)
mode=broken : 同じく「失敗すべき」出力を返す (resolved にならないべき)

grader ごとに正解/失敗の形が違う (コードは gold/ の FILE ブロック、detection は
gold findings、constraint/judge は gold_answer、qa は answer key) ため、実際の出力生成は
grader.mock_gold / mock_broken に委譲する。
"""

from __future__ import annotations

from pathlib import Path

from .base import GenerationResult, LLMClient


class MockClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.mode = cfg.get("mode", "gold")
        self.current_task = None                    # runnerが実行前にセットする Task
        self.current_task_dir: Path | None = None   # 後方互換

    def _generate(self, system: str, user: str) -> GenerationResult:
        from ..graders import get_grader

        task = self.current_task
        if task is None:
            raise RuntimeError("MockClient: current_task が未設定")
        grader = get_grader(getattr(task, "grader", "code"))
        text = (
            grader.mock_broken(task) if self.mode == "broken"
            else grader.mock_gold(task)
        )
        return GenerationResult(text=text, completion_tokens=max(1, len(text) // 4))
