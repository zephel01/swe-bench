"""OpenAI互換API クライアント (llama.cpp server / LM Studio / vLLM / API など)."""

from __future__ import annotations

import os

import requests

from .base import GenerationResult, LLMClient


def _expand_env(value: str) -> str:
    """${VAR} / $VAR を環境変数から展開する (APIキーをconfigに直書きしないため)."""
    if not isinstance(value, str):
        return value
    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    if value.startswith("$"):
        return os.environ.get(value[1:], "")
    return value


class OpenAICompatClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.base_url = cfg["base_url"].rstrip("/")
        self.model = cfg["model"]
        self.api_key = _expand_env(cfg.get("api_key", "sk-local"))

    def _generate(self, system: str, user: str) -> GenerationResult:
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {}) or {}
        return GenerationResult(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw=data,
        )
