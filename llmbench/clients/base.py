"""LLMクライアント抽象基底."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def expand_env(value, where: str = ""):
    """config値の ${VAR} / $VAR を環境変数から展開する.

    未設定の環境変数を参照した場合は ValueError (無警告で空文字に
    なって分かりにくい401等を起こさないため)。
    プレースホルダでない値はそのまま返す。
    """
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        var = value[2:-1]
    elif value.startswith("$") and len(value) > 1:
        var = value[1:]
    else:
        return value
    v = os.environ.get(var)
    if not v:
        hint = f" ({where})" if where else ""
        raise ValueError(
            f"環境変数 {var} が未設定です{hint}。"
            f"export {var}=... してから再実行してください"
        )
    return v


def require_cfg(cfg: dict, key: str, name: str, hint: str = ""):
    """必須configキーの取得。欠落時はKeyErrorでなく分かりやすいValueError."""
    if key not in cfg or cfg[key] in (None, ""):
        extra = f" {hint}" if hint else ""
        raise ValueError(f"models.{name} に {key} がありません。{extra}".rstrip())
    return cfg[key]


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
