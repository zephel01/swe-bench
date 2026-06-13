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


def fetch_served_model(base_url: str, api_key: str | None = None,
                       timeout: float = 5.0) -> str:
    """サーバが現在ロードしているモデル名を /v1/models から取得する.

    base_url は .../v1 を含む前提 (例 http://localhost:8085/v1)。
    """
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = requests.get(
        base_url.rstrip("/") + "/models", headers=headers, timeout=timeout
    )
    resp.raise_for_status()
    items = resp.json().get("data") or []
    if not items:
        raise RuntimeError("サーバがモデルを返しませんでした (/v1/models が空)")
    return items[0].get("id") or items[0].get("model") or ""


class OpenAICompatClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        self.base_url = cfg["base_url"].rstrip("/")
        self.api_key = _expand_env(cfg.get("api_key", "sk-local"))
        # model: auto / 空 のときはサーバのロード中モデルを自動採用する
        raw_model = (_expand_env(cfg.get("model", "")) or "").strip()
        self.served_model_name: str | None = None
        if raw_model.lower() in ("", "auto"):
            try:
                self.served_model_name = fetch_served_model(
                    self.base_url, self.api_key
                )
            except Exception as e:
                raise ValueError(
                    f"model: auto ですが {self.base_url}/models から"
                    f"モデル名を取得できません: {e}"
                ) from e
            self.model = self.served_model_name
        else:
            self.model = raw_model

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
