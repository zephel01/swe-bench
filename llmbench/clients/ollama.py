"""Ollama ネイティブAPI クライアント."""

from __future__ import annotations

import requests

from .base import GenerationResult, LLMClient

DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def list_ollama_models(
    base_url: str = DEFAULT_OLLAMA_HOST, timeout: float = 5.0
) -> list[str]:
    """Ollamaにインストール済みのモデル名一覧を返す (/api/tags).

    接続できない場合は requests の例外を送出する (呼び出し側で握る)。
    """
    url = base_url.rstrip("/") + "/api/tags"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return sorted(m["name"] for m in data.get("models", []) if m.get("name"))


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
