"""OpenAI互換API クライアント (llama.cpp server / LM Studio / vLLM / API など)."""

from __future__ import annotations

import json
import os
import sys
import time

import requests

from .base import GenerationResult, LLMClient, expand_env

# 後方互換: 旧APIを参照しているコード向けエイリアス (未設定時の挙動は
# 「空文字を返す」から「ValueError」に変更されている点に注意)
_expand_env = expand_env

# 通信起因の一時的失敗 (実測: QwenCloud で Read timeout が単発発生する)。
_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    ConnectionResetError,
)

# 時間を置けば直る HTTP ステータス。これだけは retry する。
#   429: レート制限 / 同時実行数超過。QwenCloud coding plan は同時実行数を
#        「負荷に応じて動的に調整」するため、--concurrency >1 で普通に踏む。
#   500/502/503/504: ゲートウェイ側の一時障害。
# それ以外の 4xx (400 不正リクエスト, 401 認証, 404 モデル名違い) は
# 何度投げても直らないので即失敗させる — 3時間のランを黙って溶かさないため。
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
# Retry-After が桁外れの値を返してきたときの上限 (秒)
_MAX_RETRY_AFTER = 120.0


class RetryableHTTPError(RuntimeError):
    """時間を置けば直る見込みのある HTTP エラー (429/5xx)."""

    def __init__(self, message: str, status: int, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _opt(value, cast):
    """未指定 (None/空文字) なら None、それ以外は cast した値を返す.

    「送らない」と「0 を送る」は別物 (top_k=0 は無効化の意味を持つ) なので、
    0 や 0.0 をうっかり None に潰さないよう明示的に None だけを弾く。
    """
    if value is None or value == "":
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _parse_retry_after(value: str | None) -> float | None:
    """Retry-After ヘッダ (秒数形式) を float で返す. 不正値は None."""
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except (TypeError, ValueError):
        return None                      # HTTP-date 形式は未対応 (バックオフに委ねる)
    if seconds < 0:
        return None
    return min(seconds, _MAX_RETRY_AFTER)


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
        # サンプリング設定。**送っていなかったものは効いていない**:
        # llama-server の既定は seed=-1 (毎回ランダム) なので、seed を送らない
        # 限り「同じ条件で測った」とは言えない。None のものは payload に載せず
        # サーバ既定に従う (従来動作と同一)。
        self.top_p = _opt(cfg.get("top_p"), float)
        self.top_k = _opt(cfg.get("top_k"), int)
        self.min_p = _opt(cfg.get("min_p"), float)
        self.seed = _opt(cfg.get("seed"), int)
        # ストリーミング (stream: true)。長時間生成では実質必須。
        #   非ストリームだと生成が終わるまで1バイトも流れてこないため、
        #     (1) requests の read timeout が「生成全体の制限時間」として効く
        #         → max_tokens / スループット で決まる生成時間が timeout を
        #           超えた瞬間に Read timed out で落ちる
        #     (2) 無通信のまま数分〜数十分続く接続を中間ゲートウェイが切る
        #         → ('Connection aborted.', ConnectionResetError(54, ...))
        #   stream: true にすると read timeout は「チャンク間隔」に対して効く
        #   ようになり、どちらの問題も消える。
        #   思考(thinking)モデル + 大きな max_tokens の組み合わせでは必ず有効化すること。
        self.stream = bool(cfg.get("stream", False))
        # reasoning_effort: 思考モデルの推論予算 (QwenCloud: low/medium/xhigh)。
        # 未指定なら送らない = サーバ既定に従う (qwen3.8-max の既定は xhigh)。
        self.reasoning_effort = cfg.get("reasoning_effort") or None
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

    def _build_payload(self, system: str, user: str) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        # None でないものだけ送る (未指定はサーバ既定に従う = 従来動作)
        for key, value in (
            ("top_p", self.top_p), ("top_k", self.top_k),
            ("min_p", self.min_p), ("seed", self.seed),
        ):
            if value is not None:
                payload[key] = value
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.stream:
            payload["stream"] = True
            # usage (completion_tokens) はストリームでは既定で返らない。
            # tok/s の計測に必要なので明示的に要求する。
            # 未対応サーバは無視するだけなので付けて害はない。
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _consume_stream(self, resp) -> tuple[str, str, dict, str | None]:
        """SSE を読み切って (content, reasoning, usage, finish_reason) を返す."""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage: dict = {}
        finish_reason: str | None = None
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if line.startswith(":"):        # SSE コメント (keep-alive)
                continue
            if not line.startswith("data:"):
                continue
            body = line[len("data:"):].strip()
            if body == "[DONE]":
                break
            try:
                chunk = json.loads(body)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"] or {}
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    content_parts.append(delta["content"])
                reasoning = (
                    delta.get("reasoning_content") or delta.get("reasoning") or ""
                )
                if reasoning:
                    reasoning_parts.append(reasoning)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
        return "".join(content_parts), "".join(reasoning_parts), usage, finish_reason

    def _finalize(
        self, content: str, reasoning: str, usage: dict,
        finish_reason: str | None, raw: dict,
    ) -> GenerationResult:
        """content/reasoning/usage から GenerationResult を組み立てる (共通処理)."""
        completion_tokens = usage.get("completion_tokens")
        text = content
        # 打ち切り判定: finish_reason=length か、completion_tokens が
        # max_tokens に到達しているか。どちらも「続きがあったのに切られた」印。
        truncated = bool(finish_reason == "length") or bool(
            completion_tokens and completion_tokens >= self.max_tokens
        )
        if finish_reason == "length":
            # 旧実装は `and content.strip()` を条件に付けていたため、
            # **content が空＝最も危険な場面でこの警告が出なかった**。条件を外す。
            print(
                f"⚠️ {self.name}: finish_reason=length — max_tokens="
                f"{self.max_tokens} で出力が打ち切られています "
                f"(completion_tokens={completion_tokens})。"
                "max_tokens 引き上げ、または reasoning_effort の抑制を検討してください",
                file=sys.stderr,
            )
        if not content.strip():
            # 推論(thinking)系モデル対策: llama.cpp/vLLM等はreasoning_format設定時、
            # <think>...</think> を reasoning_content (別フィールド) に分離し、
            # </think> を閉じる前に生成が終わると content が空のまま返ってくる。
            # 答えがreasoning側に紛れ込んでいる場合があるのでフォールバックで拾う。
            if reasoning.strip():
                text = reasoning
                # content が空のまま返るのは「</think> を閉じる前に生成が
                # 終わった」= 思考が予算内に完了していない状態なので、
                # フォールバックで拾えても打ち切り扱いにする。
                truncated = True
                print(
                    f"⚠️ {self.name}: content が空。reasoning_content "
                    f"({len(reasoning)}文字) にフォールバックしてパースを試みます"
                    f" — 思考が予算内に完了しておらず (max_tokens={self.max_tokens}, "
                    f"completion_tokens={completion_tokens})、"
                    "ここから抽出したコードは信頼できない可能性があります",
                    file=sys.stderr,
                )
            elif completion_tokens and completion_tokens >= self.max_tokens:
                print(
                    f"⚠️ {self.name}: 出力が空 (content/reasoning_content とも空) — "
                    f"completion_tokens={completion_tokens} が max_tokens="
                    f"{self.max_tokens} に到達しています。推論(thinking)が予算内に"
                    "完了しなかった可能性が高いです"
                    "(対策: max_tokens引き上げ、または推論の抑制を検討)",
                    file=sys.stderr,
                )
            else:
                print(
                    f"⚠️ {self.name}: 出力が空 (content/reasoning_content とも空、"
                    f"completion_tokens={completion_tokens}, max_tokens未到達) — "
                    "生成が早期に停止した可能性があります",
                    file=sys.stderr,
                )
            if not text.strip():
                # 空白のみのcontentも空として扱う(patch.py側の判定と揃える)
                text = ""
        return GenerationResult(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
            truncated=truncated,
            max_tokens=self.max_tokens,
            raw=raw,
        )

    def _post_once(self, system: str, user: str) -> GenerationResult:
        """1回だけ /chat/completions を叩いて GenerationResult を返す (retryなし)."""
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=self._build_payload(system, user),
            timeout=self.timeout,
            stream=self.stream,
        )
        # 注: with 文 (コンテキストマネージャ) は使わない。既存テストの
        # レスポンスモックが __enter__/__exit__ を持たないため。
        # ストリーム時だけ、途中で例外が出ても接続を解放する。
        try:
            if resp.status_code >= 400:
                body = (resp.text or "").strip().replace("\n", " ")
                msg = (
                    f"{resp.status_code} {resp.reason} from "
                    f"{self.base_url}/chat/completions: {body[:500]}"
                )
                if resp.status_code in _RETRYABLE_STATUS:
                    raise RetryableHTTPError(
                        msg, resp.status_code,
                        _parse_retry_after(resp.headers.get("Retry-After")),
                    )
                raise RuntimeError(msg)
            if self.stream:
                content, reasoning, usage, finish_reason = self._consume_stream(resp)
                raw = {
                    "stream": True,
                    "usage": usage,
                    "finish_reason": finish_reason,
                }
            else:
                data = resp.json()
                usage = data.get("usage", {}) or {}
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content") or ""
                reasoning = (
                    message.get("reasoning_content") or message.get("reasoning") or ""
                )
                finish_reason = choice.get("finish_reason")
                raw = data
        finally:
            if self.stream:
                resp.close()
        return self._finalize(content, reasoning, usage, finish_reason, raw)

    def _generate(self, system: str, user: str) -> GenerationResult:
        """一時的失敗を指数バックオフで再試行する ``_post_once`` ラッパ.

        再試行対象:
          - ``_TRANSIENT_ERRORS`` (ConnectionError / Timeout /
            ConnectionResetError / ChunkedEncodingError)
          - ``_RETRYABLE_STATUS`` の HTTP エラー (429 / 500 / 502 / 503 / 504)。
            429 の Retry-After ヘッダがあればその秒数を優先する。
        それ以外の 4xx (400/401/404 など) は retry しない
        (原因が呼び出し側にあるため retry しても直らない)。
        """
        retryable = _TRANSIENT_ERRORS + (RetryableHTTPError,)
        last_exc: BaseException | None = None
        for attempt in range(self.transient_retries + 1):
            try:
                return self._post_once(system, user)
            except retryable as e:
                last_exc = e
                if attempt < self.transient_retries:
                    delay = self.transient_backoff * (2 ** attempt)
                    hint = ""
                    if isinstance(e, RetryableHTTPError) and e.retry_after is not None:
                        delay = e.retry_after
                        hint = " (Retry-After)"
                    print(
                        f"⚠️ transient error on {self.name} "
                        f"(attempt {attempt + 1}/{self.transient_retries + 1}): "
                        f"{type(e).__name__}: {str(e)[:120]} — "
                        f"retry in {delay:.1f}s{hint}",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                break
        assert last_exc is not None
        raise last_exc
