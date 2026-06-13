"""Ollama ネイティブAPI クライアント."""

from __future__ import annotations

import requests

from .base import GenerationResult, LLMClient


class OllamaClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.base_url = cfg.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = cfg["model"]

    def _generate(self, system: str, user: str) -> GenerationResult:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollamaはeval_count/eval_durationを返す (durationはナノ秒)
        completion_tokens = data.get("eval_count")
        eval_ns = data.get("eval_duration")
        latency = eval_ns / 1e9 if eval_ns else 0.0
        return GenerationResult(
            text=data["message"]["content"],
            latency_sec=latency,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=completion_tokens,
            raw=data,
        )
