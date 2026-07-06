"""OpenAI互換API クライアント (llama.cpp server / LM Studio / vLLM / API など)."""

from __future__ import annotations

import os
import sys

import requests

from .base import GenerationResult, LLMClient, expand_env

# 後方互換: 旧APIを参照しているコード向けエイリアス (未設定時の挙動は
# 「空文字を返す」から「ValueError」に変更されている点に注意)
_expand_env = expand_env


def fetch_served_model(base_url: str, api_key: str | None = None,
                       timeout: float = 5.0, prefer: str | None = None) -> str:
    """サーバが現在ロードしているモデル名を /v1/models から取得する.

    base_url は .../v1 を含む前提 (例 http://localhost:8085/v1)。
    prefer に部分文字列を渡すと、複数モデルロード時にそれを含む
    最初のモデルを優先採用する (大文字小文字は無視)。
    """
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = requests.get(
        base_url.rstrip("/") + "/models", headers=headers, timeout=timeout
    )
    resp.raise_for_status()
    items = resp.json().get("data") or []
    if not items:
        raise RuntimeError("サーバがモデルを返しませんでした (/v1/models が空)")
    names = [it.get("id") or it.get("model") or "" for it in items]
    if prefer:
        for n in names:
            if prefer.lower() in n.lower():
                return n
        raise RuntimeError(
            f"auto_prefer={prefer!r} に一致するモデルがありません。"
            f"ロード中: {names}"
        )
    if len(names) > 1:
        print(
            f"⚠️ 複数モデルがロード中 {names} → 先頭 {names[0]!r} を採用します"
            " (auto_prefer で選択可能)",
            file=sys.stderr,
        )
    return names[0]


class OpenAICompatClient(LLMClient):
    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        # base_url: config (${VAR}展開) > 環境変数 OPENAI_BASE_URL
        raw_url = cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL", "")
        raw_url = expand_env(raw_url, where=f"models.{name}.base_url")
        if not raw_url:
            raise ValueError(
                f"models.{name} に base_url がありません "
                "(config で指定するか OPENAI_BASE_URL を設定してください)"
            )
        self.base_url = str(raw_url).rstrip("/")
        self.api_key = expand_env(
            cfg.get("api_key", "sk-local"), where=f"models.{name}.api_key"
        )
        # model: auto / 空 のときはサーバのロード中モデルを自動採用する
        raw_model = (
            expand_env(cfg.get("model", ""), where=f"models.{name}.model") or ""
        ).strip()
        self.served_model_name: str | None = None
        if raw_model.lower() in ("", "auto"):
            try:
                self.served_model_name = fetch_served_model(
                    self.base_url, self.api_key,
                    prefer=cfg.get("auto_prefer"),
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
