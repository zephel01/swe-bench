"""OpenAI互換API クライアント (llama.cpp server / LM Studio / vLLM / API など)."""

from __future__ import annotations

import os
import sys
import time

import requests

from .base import GenerationResult, LLMClient, expand_env

# 後方互換: 旧APIを参照しているコード向けエイリアス (未設定時の挙動は
# 「空文字を返す」から「ValueError」に変更されている点に注意)
_expand_env = expand_env

# 通信起因の一時的失敗 (実測: QwenCloud で Read timeout が単発発生する)。
# HTTP 4xx/5xx はビジネスロジック側で扱うのでここには含めない。
_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    ConnectionResetError,
)


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
        # 通信リトライ設定: 通信起因の一時的失敗のみ、指数バックオフで再試行
        # 既定 2 回 (合計 3 回試行)。config の transient_retries で上書き可能。
        # HTTP 4xx/5xx はここでは retry しない (呼び出し側で扱う)。
        self.transient_retries = int(cfg.get("transient_retries", 2))
        self.transient_backoff = float(cfg.get("transient_backoff", 2.0))
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

    def _post_once(self, system: str, user: str) -> GenerationResult:
        """1回だけ /chat/completions を叩いて GenerationResult を返す (retryなし)."""
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
        if resp.status_code >= 400:
            body = (resp.text or "").strip().replace("\n", " ")
            raise RuntimeError(
                f"{resp.status_code} {resp.reason} from "
                f"{self.base_url}/chat/completions: {body[:500]}"
            )
        data = resp.json()
        usage = data.get("usage", {}) or {}
        return GenerationResult(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw=data,
        )

    def _generate(self, system: str, user: str) -> GenerationResult:
        """通信起因の一時的失敗を指数バックオフで再試行する ``_post_once`` ラッパ.

        再試行対象は ``_TRANSIENT_ERRORS`` のみ (ConnectionError / Timeout /
        ConnectionResetError / ChunkedEncodingError)。HTTP 4xx/5xx や JSON パース
        エラーは retry しない (原因が呼び出し側にあるため retry しても直らない)。
        """
        last_exc: BaseException | None = None
        for attempt in range(self.transient_retries + 1):
            try:
                return self._post_once(system, user)
            except _TRANSIENT_ERRORS as e:
                last_exc = e
                if attempt < self.transient_retries:
                    delay = self.transient_backoff * (2 ** attempt)
                    print(
                        f"⚠️ transient error on {self.name} "
                        f"(attempt {attempt + 1}/{self.transient_retries + 1}): "
                        f"{type(e).__name__}: {str(e)[:120]} — retry in {delay:.1f}s",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                break
        assert last_exc is not None
        raise last_exc
