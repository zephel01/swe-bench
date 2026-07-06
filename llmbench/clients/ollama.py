"""Ollama ネイティブAPI クライアント."""

from __future__ import annotations

import os

import requests

from .base import GenerationResult, LLMClient, expand_env, require_cfg

DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def default_ollama_host() -> str:
    """Ollama既定ホスト: 環境変数 OLLAMA_HOST > localhost:11434."""
    return os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST


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
        raw_url = cfg.get("base_url") or default_ollama_host()
        raw_url = expand_env(raw_url, where=f"models.{name}.base_url")
        self.base_url = str(raw_url).rstrip("/")
        self.model = require_cfg(
            cfg, "model", name, hint="(例: model: qwen2.5-coder:32b)"
        )

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
