"""LLMクライアント層: OpenAI互換 / Ollama / Mock."""

from .base import GenerationResult as GenerationResult
from .base import LLMClient
from .openai_compat import OpenAICompatClient
from .ollama import OllamaClient
from .mock import MockClient


def create_client(name: str, cfg: dict) -> LLMClient:
    """config.yaml の models エントリからクライアントを生成する."""
    ctype = cfg.get("type")
    if ctype == "openai":
        return OpenAICompatClient(name, cfg)
    if ctype == "ollama":
        return OllamaClient(name, cfg)
    if ctype == "mock":
        return MockClient(name, cfg)
    raise ValueError(f"unknown client type: {ctype!r} (model={name})")
