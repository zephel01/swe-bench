"""検証用モッククライアント.

mode=gold   : タスクの gold/ ディレクトリの内容を正規フォーマットで返す
mode=broken : 構文の壊れたpatchを返す (resolved=0 系統の検証用)
"""

from __future__ import annotations

from pathlib import Path

from .base import GenerationResult, LLMClient


class MockClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.mode = cfg.get("mode", "gold")
        self.current_task_dir: Path | None = None  # runnerが実行前にセットする

    def _generate(self, system: str, user: str) -> GenerationResult:
        if self.mode == "broken":
            return GenerationResult(
                text="raise SyntaxError(  # 壊れた出力 (フォーマット不正かつ非Python)",
                completion_tokens=10,
            )
        if self.current_task_dir is None:
            raise RuntimeError("MockClient: current_task_dir が未設定")
        gold = self.current_task_dir / "gold"
        blocks = []
        for f in sorted(gold.rglob("*.py")):
            rel = f.relative_to(gold)
            blocks.append(f"--- FILE: {rel} ---\n```python\n{f.read_text()}\n```")
        text = "修正は以下の通りです。\n\n" + "\n\n".join(blocks)
        return GenerationResult(text=text, completion_tokens=len(text) // 4)
