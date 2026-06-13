"""LLMクライアント抽象基底."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """1回の生成結果. 速度メトリクス込み."""

    text: str
    latency_sec: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict = field(default_factory=dict)

    @property
    def tokens_per_sec(self) -> float | None:
        if self.completion_tokens and self.latency_sec > 0:
            return self.completion_tokens / self.latency_sec
        return None


class LLMClient(ABC):
    """OpenAI互換 / Ollama / Mock 共通インタフェース."""

    def __init__(self, name: str, cfg: dict):
        self.name = name
        self.cfg = cfg
        self.temperature = float(cfg.get("temperature", 0.2))
        self.max_tokens = int(cfg.get("max_tokens", 4096))
        self.timeout = int(cfg.get("timeout", 600))

    @abstractmethod
    def _generate(self, system: str, user: str) -> GenerationResult:
        """system/userプロンプトから生成する. 実装はサブクラスで."""

    def generate(self, system: str, user: str) -> GenerationResult:
        """生成 + レイテンシ計測のラッパ."""
        t0 = time.monotonic()
        result = self._generate(system, user)
        if result.latency_sec == 0.0:
            result.latency_sec = time.monotonic() - t0
        return result
