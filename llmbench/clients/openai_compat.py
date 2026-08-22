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

# ── 思考(reasoning)暴走ガードの既定値 ────────────────────────────────
# 背景: 思考モデル (Qwen3.8 系 GGUF など) は難問で縮退ループに落ちることがある。
#   実測: content が空のまま reasoning_content だけが伸び続け、
#         "1,1,1,1,..." を1行 15,434 文字 / 同一文を 1,552 行 のように
#         同じ断片を反復したまま max_tokens (49,152) に到達する。
#   このとき生成は必ず失敗するのに、1回あたり max_tokens 分の時間を丸ごと
#   消費する (49,152tok @ 330tok/s ≒ 150秒)。runs=5 × generate_retries=1 なら
#   1タスクで最大10回 = 25分。frontier 帯が続くとランが実質止まって見える。
# 対策: ストリーミング中に反復を検出した時点で接続を切る。
#
# ⚠️ 2026-08-18 追記 — 「本文が出たら止めない」だけでは足りなかった。
#   t048 (architect) で content が非空のまま 49,152 トークンに到達した。
#   同じタスクの正答は他モデルで 2,109〜2,449 バイト (≒600〜700tok)、gold は
#   2ファイル59行。60〜80倍は「大きい答えが切れた」ではなく本文側の暴走。
#   さらに、サーバが <think> を reasoning_content に分離しない構成では
#   最初の思考トークンで content が非空になり、思考側ガードが1トークン目から
#   無効化されてしまう。そこで:
#     ・content 中の <think>…</think> は「思考」として扱い、思考側ガードを効かせる
#     ・think の外 (= 本文) にも反復ガードを入れる。ただし正答の数倍という
#       余裕を持ったしきい値で、明確な縮退だけを捕まえる
_LOOP_GUARD_MIN_CHARS = 8000      # これ未満の思考は判定しない (正常な長考を殺さない)
_LOOP_GUARD_INTERVAL = 4000       # 何文字進むごとに判定するか
_LOOP_GUARD_TAIL = 3000           # 末尾何文字を検査対象にするか
_LOOP_GUARD_MAX_PERIOD = 400      # 反復単位の最大長 (これより長い周期は見ない)
_LOOP_GUARD_MIN_REPEATS = 6       # 何回連続で繰り返したらループとみなすか
_LOOP_GUARD_MIN_LINES = 20        # 行反復判定に必要な最小行数
_LOOP_GUARD_DUP_LINE_RATIO = 0.8  # 重複行の割合がこれ以上ならループとみなす
# 本文側の判定開始しきい値。実測の正答 2,109〜2,449 バイトに対して約7倍。
# コードは繰り返しの多い行 (import/dictリテラル) を含むので、思考側より
# 大きく取って「明らかに書きすぎている」ときだけ見る。
_CONTENT_LOOP_MIN_CHARS = 16000

# 打ち切り理由 (finish_reason に入れる合成値)。サーバ由来の値
# (stop/length/...) と衝突しないよう llmbench 独自の接頭辞を付ける。
FINISH_REASONING_LOOP = "llmbench:reasoning_loop"
FINISH_REASONING_BUDGET = "llmbench:reasoning_budget"
FINISH_CONTENT_LOOP = "llmbench:content_loop"


def find_repeating_unit(
    tail: str,
    max_period: int = _LOOP_GUARD_MAX_PERIOD,
    min_repeats: int = _LOOP_GUARD_MIN_REPEATS,
) -> str | None:
    """``tail`` の末尾が短い単位の完全反復なら、その単位を返す (無ければ None).

    "1,1,1,1,..." のようなトークン単位のループも、同一文の行単位ループも
    同じ判定で拾える。周期 p を短い順に試し、末尾 p*min_repeats 文字が
    単位の単純な繰り返しになっているかだけを見る。

    ⚠️ 空白だけの単位は無視する。これを見ないと、末尾が改行6連続や
    インデント6連続になっているだけの正常な出力を「反復」と誤判定する
    (コードブロックの末尾では普通に起きる)。
    """
    n = len(tail)
    if n < min_repeats:
        return None
    for p in range(1, min(max_period, n // min_repeats) + 1):
        unit = tail[-p:]
        if not unit.strip():
            continue                     # 空白のみの単位は反復とみなさない
        if tail[-p * min_repeats:] == unit * min_repeats:
            return unit
    return None


def duplicate_line_ratio(tail: str, min_lines: int = _LOOP_GUARD_MIN_LINES) -> float:
    """``tail`` 内の重複行の割合 (0.0〜1.0). 行数が足りなければ 0.0.

    完全反復ではないが同じ文を延々と繰り返しているケースを拾うための、
    ゆるい第2判定。先頭行は途中で切れている可能性があるので捨てる。
    """
    lines = [ln.strip() for ln in tail.splitlines()[1:] if ln.strip()]
    if len(lines) < min_lines:
        return 0.0
    return 1.0 - len(set(lines)) / len(lines)


def detect_reasoning_loop(tail: str) -> str | None:
    """思考テキストの末尾がループしていれば、人間向けの説明文を返す."""
    unit = find_repeating_unit(tail)
    if unit is not None:
        shown = unit if len(unit) <= 40 else unit[:40] + "…"
        return f"{len(unit)}文字の単位が{_LOOP_GUARD_MIN_REPEATS}回以上反復: {shown!r}"
    ratio = duplicate_line_ratio(tail)
    if ratio >= _LOOP_GUARD_DUP_LINE_RATIO:
        return f"直近の行の{ratio * 100:.0f}%が重複"
    return None


_THINK_OPEN = ("<think>", "<thinking>")
_THINK_CLOSE = ("</think>", "</thinking>")
# タグがチャンク境界で分断されても取りこぼさないよう、末尾をこの長さだけ
# 次回に持ち越す (最長タグ長 - 1)。
_THINK_CARRY = max(len(t) for t in _THINK_OPEN + _THINK_CLOSE) - 1


class ThinkSplitter:
    """content ストリームを「思考 (<think>内)」と「本文」に振り分ける.

    サーバによっては思考を ``reasoning_content`` に分離せず、``content`` に
    ``<think>…</think>`` のまま流してくる (llama.cpp の --reasoning-format 次第。
    非ストリームでは分離されるのにストリームでは分離されない構成もある)。
    その場合 content は最初の思考トークンで非空になるので、「本文が出たら
    ガードを外す」という判定が1トークン目から効かなくなる。ここで振り分けて
    おけば、分離するサーバでもしないサーバでも同じガードが働く。

    タグが見つからない (= 素直に本文だけを返すサーバ) ときは、全部が本文に
    なるので従来と同じ挙動になる。
    """

    def __init__(self) -> None:
        self.in_think = False
        self._carry = ""

    @staticmethod
    def _partial_tag_len(buf: str) -> int:
        """``buf`` の末尾が何文字ぶんタグの途中になりうるか (0 なら持ち越し不要).

        無条件に末尾を持ち越すと、タグを一切使わないサーバでも本文の
        検出が最大10文字ぶん遅れる。ここでタグの前方一致だけを見て、
        本当に途中でありうるときだけ持ち越す。
        """
        tags = _THINK_OPEN + _THINK_CLOSE
        for k in range(min(_THINK_CARRY, len(buf)), 0, -1):
            suffix = buf[-k:]
            if any(t.startswith(suffix) for t in tags):
                return k
        return 0

    def feed(self, chunk: str) -> tuple[str, str]:
        """チャンクを (思考として扱う分, 本文として扱う分) に分けて返す."""
        buf = self._carry + chunk
        keep = self._partial_tag_len(buf)
        self._carry, buf = buf[len(buf) - keep:] if keep else "", (
            buf[:len(buf) - keep] if keep else buf
        )
        return self._split(buf)

    def flush(self) -> tuple[str, str]:
        """ストリーム終了時に持ち越し分を吐き出す."""
        buf, self._carry = self._carry, ""
        return self._split(buf)

    def _split(self, buf: str) -> tuple[str, str]:
        think_parts: list[str] = []
        body_parts: list[str] = []
        while buf:
            tags = _THINK_CLOSE if self.in_think else _THINK_OPEN
            hits = [(buf.find(t), t) for t in tags]
            hits = [(i, t) for i, t in hits if i >= 0]
            if not hits:
                (think_parts if self.in_think else body_parts).append(buf)
                break
            idx, tag = min(hits)
            if idx:
                (think_parts if self.in_think else body_parts).append(buf[:idx])
            # タグ自体は思考側に数える (本文の一部ではない)
            think_parts.append(tag)
            self.in_think = not self.in_think
            buf = buf[idx + len(tag):]
        return "".join(think_parts), "".join(body_parts)


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


def list_remote_models(base_url: str, api_key: str | None = None,
                       timeout: float = 10.0) -> list[dict]:
    """/v1/models が提供する全モデルの生データを返す (id / owned_by 等).

    fetch_served_model は「ローカルサーバが今ロードしている1つ」を選び取る
    用途 (model: auto の自動解決) だが、こちらは OpenCode Go のように
    1つのエンドポイントで複数モデルを選べるゲートウェイに向けて、
    **一覧そのもの** を返す (`llmbench models --remote <名前>` から使う)。
    空リストは「モデル0件」として正常に返す (エラーにしない) — 取得の可否と
    件数0は別の状態なので、呼び出し側でメッセージを分けられるようにする。
    接続できない/認証エラー等は requests の例外をそのまま送出する
    (呼び出し側で握る)。
    """
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = requests.get(
        base_url.rstrip("/") + "/models", headers=headers, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json().get("data") or []


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
        # ── 思考(reasoning)暴走ガード ──────────────────────────────
        # どちらも「本文(content)がまだ1文字も出ていない」間だけ働く。
        # 本文が出始めた生成は打ち切らないので、正常な長考は壊さない。
        #   loop_guard: 反復(縮退ループ)を検出したら即座に接続を切る。既定 ON。
        #   reasoning_max_tokens: 思考の上限。SSEのdeltaチャンク数を
        #     トークン数の近似として数える (サーバが複数トークンをまとめて
        #     送る場合は少なめに数える = ガードが早発しない側に倒れる)。
        self.loop_guard = bool(cfg.get("loop_guard", True))
        self.reasoning_max_tokens = _opt(cfg.get("reasoning_max_tokens"), int)
        if not self.stream and (
            self.reasoning_max_tokens or "loop_guard" in cfg
        ):
            print(
                f"⚠️ {self.name}: loop_guard / reasoning_max_tokens は "
                "stream: true のときだけ働きます (非ストリームでは生成が"
                "終わるまで1バイトも届かないため途中で打ち切れません)。"
                "config に stream: true を追加してください",
                file=sys.stderr,
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

    def _consume_stream(self, resp) -> tuple[str, str, dict, str | None, str]:
        """SSE を読み切って (content, reasoning, usage, finish_reason, abort) を返す.

        ``abort`` は暴走ガードが接続を切ったときだけ非空になる
        (ガードが働かなければ従来どおり空文字)。

        ガードは2段。``content`` 中の ``<think>…</think>`` は思考として扱うので、
        サーバが reasoning_content に分離してもしなくても同じ判定になる。
          1. 本文がまだ出ていない間 … 思考の反復 / 思考トークン上限
          2. 本文が出始めてから    … 本文の反復 (しきい値は大きめ)
        """
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage: dict = {}
        finish_reason: str | None = None
        abort = ""
        # ガード用の状態。tail は末尾 _LOOP_GUARD_TAIL 文字だけ持ち回る
        # (180,000 文字の思考でも毎回フル結合しないため)。
        splitter = ThinkSplitter()
        tail = ""                     # 思考テキストの末尾
        reasoning_chars = 0
        reasoning_chunks = 0
        next_check = _LOOP_GUARD_MIN_CHARS
        body_tail = ""                # 本文の末尾
        body_chars = 0                # 本文の文字数 (<think> の外)
        body_started = False          # 本文に空白以外が出たか
        next_body_check = _CONTENT_LOOP_MIN_CHARS
        bad_chunks = 0                # JSON として読めず捨てた SSE 行

        # ⚠️ SSE の文字コードを明示する (2026-08-19 実害あり)。
        # llama.cpp / vLLM は `Content-Type: text/event-stream` を charset 無しで
        # 返す。requests は RFC 2616 に従い text/* の既定を ISO-8859-1 と解釈する
        # ため、`iter_lines(decode_unicode=True)` が UTF-8 のバイト列を latin-1 で
        # 復号してしまう。結果、日本語の応答は
        #   1. 文字化けする (「野獣」→「éç£」。文字数も約3倍に膨らむ)
        #   2. **黙って欠落する** — latin-1 復号後の文字列には U+0085 (NEL) 等が
        #      現れ、str.splitlines() がそこを改行とみなして SSE 行を分断する。
        #      分断された行は json.loads に失敗し、下の except で捨てられる。
        # 実測: --lang ja のランで char_count が3倍になり、日本語キーワードの
        # contains/regex が全滅、生成タスクが誤って不合格になっていた。
        resp.encoding = "utf-8"

        def _add_think(text: str) -> None:
            """ガード用に「思考テキスト」を積む.

            ここに来るのは (a) reasoning_content フィールド と
            (b) content 中の <think>…</think> の2経路。(b) は content 側に
            そのまま残っているので、返り値の reasoning には積まない
            (積むと同じ文字列が二重に出てフォールバック判定を狂わせる)。
            """
            nonlocal tail, reasoning_chars, reasoning_chunks
            if not text:
                return
            reasoning_chars += len(text)
            reasoning_chunks += 1
            tail = (tail + text)[-_LOOP_GUARD_TAIL:]

        def _add_body(text: str) -> None:
            nonlocal body_tail, body_chars, body_started
            if not text:
                return
            body_chars += len(text)
            body_tail = (body_tail + text)[-_LOOP_GUARD_TAIL:]
            if text.strip():
                body_started = True

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
                # 本来ここには来ない。来るならサーバが壊れた SSE を吐いたか、
                # 文字コードの取り違えで行が分断されている (上の resp.encoding
                # 参照)。黙って捨てるとモデル出力が欠けたまま採点されるので、
                # 数えて最後に警告する。
                bad_chunks += 1
                continue
            if chunk.get("usage"):
                usage = chunk["usage"] or {}
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    content_parts.append(delta["content"])
                    # content 内の <think>…</think> は思考として数える
                    think_text, body_text = splitter.feed(delta["content"])
                    _add_think(think_text)
                    _add_body(body_text)
                reasoning = (
                    delta.get("reasoning_content") or delta.get("reasoning") or ""
                )
                if reasoning:
                    reasoning_parts.append(reasoning)
                    _add_think(reasoning)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
            if not body_started:
                # ── 段1: まだ本文が出ていない = 思考中 ──
                # トークン数の推定: SSE の delta 数と 文字数÷4 の大きい方。
                #   llama.cpp は1トークン1チャンクで送るので delta 数がそのまま
                #   トークン数になる。まとめて送るサーバでは delta 数が過小に
                #   なるので、文字数からの見積り (実測 3.65 文字/トークン、
                #   安全側に 4) で補う。どちらも過小側に倒れる = 早発しない。
                if self.reasoning_max_tokens:
                    est_tokens = max(reasoning_chunks, reasoning_chars // 4)
                    over = est_tokens >= self.reasoning_max_tokens
                else:
                    over = False
                if over:
                    abort = (
                        f"思考が上限 {self.reasoning_max_tokens} トークンに到達"
                        f" (本文は未出力 / 思考 {reasoning_chars:,}文字)"
                    )
                    finish_reason = FINISH_REASONING_BUDGET
                    break
                if self.loop_guard and reasoning_chars >= next_check:
                    next_check = reasoning_chars + _LOOP_GUARD_INTERVAL
                    hit = detect_reasoning_loop(tail)
                    if hit:
                        abort = (
                            f"思考が縮退ループに陥っています ({hit})"
                            f" / 思考 {reasoning_chars:,}文字 で打ち切り"
                        )
                        finish_reason = FINISH_REASONING_LOOP
                        break
            elif self.loop_guard and body_chars >= next_body_check:
                # ── 段2: 本文を書いている最中の縮退 ──
                # ここまで書いて反復に入っているなら、その答えはもう壊れている。
                # ただし本文は捨てない (縮退より前に正しいブロックが書かれて
                # いる可能性があるので、grader に判断させる)。
                next_body_check = body_chars + _LOOP_GUARD_INTERVAL
                hit = detect_reasoning_loop(body_tail)
                if hit:
                    abort = (
                        f"本文が縮退ループに陥っています ({hit})"
                        f" / 本文 {body_chars:,}文字 で打ち切り"
                    )
                    finish_reason = FINISH_CONTENT_LOOP
                    break
        # 持ち越し分 (タグ途中で終わった場合) を吐き出しておく。
        # 集計値の整合のためで、返す content/reasoning には影響しない。
        _add_think(splitter.flush()[0])
        if bad_chunks:
            # モデル出力が欠けたまま採点される事故を黙って通さない。
            print(
                f"⚠️  {self.name}: SSE を {bad_chunks} 行パースできず捨てました "
                f"(応答が欠けている可能性があります)",
                file=sys.stderr,
            )
        return (
            "".join(content_parts), "".join(reasoning_parts),
            usage, finish_reason, abort,
        )

    def _finalize(
        self, content: str, reasoning: str, usage: dict,
        finish_reason: str | None, raw: dict, abort: str = "",
    ) -> GenerationResult:
        """content/reasoning/usage から GenerationResult を組み立てる (共通処理).

        ``abort`` が非空なら暴走ガードが接続を切った生成。無条件で
        打ち切り扱いにする (max_tokens には到達していないため)。
        """
        completion_tokens = usage.get("completion_tokens")
        text = content
        # 打ち切り判定: finish_reason=length か、completion_tokens が
        # max_tokens に到達しているか。どちらも「続きがあったのに切られた」印。
        truncated = bool(finish_reason == "length") or bool(
            completion_tokens and completion_tokens >= self.max_tokens
        )
        if abort:
            truncated = True
            tail_note = (
                "本文はここまでの分を採点に回します"
                if finish_reason == FINISH_CONTENT_LOOP
                else "この試行は失敗として記録され、残りの試行はスキップされます"
            )
            print(
                f"⛔ {self.name}: 暴走ガードで生成を打ち切りました — {abort}。"
                f"{tail_note} "
                "(config: loop_guard / reasoning_max_tokens)",
                file=sys.stderr,
            )
        if abort and finish_reason == FINISH_CONTENT_LOOP:
            # 本文側の打ち切りは、縮退より前に正しいブロックが書かれている
            # 可能性があるので content を捨てない。打ち切り印だけ付けて返す。
            return GenerationResult(
                text=content,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=completion_tokens,
                finish_reason=finish_reason,
                truncated=True,
                max_tokens=self.max_tokens,
                raw=raw,
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
        if abort:
            # ガードで切った思考は「同じ断片の反復」なので、reasoning への
            # フォールバックはしない。180,000文字の縮退テキストを grader に
            # 食わせても抽出できるコードは無く、採点時間を捨てるだけ。
            return GenerationResult(
                text="",
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=completion_tokens,
                finish_reason=finish_reason,
                truncated=True,
                max_tokens=self.max_tokens,
                raw=raw,
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
            abort = ""
            if self.stream:
                content, reasoning, usage, finish_reason, abort = (
                    self._consume_stream(resp)
                )
                raw = {
                    "stream": True,
                    "usage": usage,
                    "finish_reason": finish_reason,
                    "abort": abort,
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
        return self._finalize(content, reasoning, usage, finish_reason, raw, abort)

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
