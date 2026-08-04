"""ストリーミング(stream: true)対応の単体テスト (ネットワーク不要・全てモック).

背景: qwen3.8-max (思考モデル) で Read timeout / Connection reset が多発した。
原因は非ストリームだと
  (1) requests の read timeout が「生成全体の制限時間」として効く
  (2) 無通信のまま続く接続を中間ゲートウェイが切る
の2点。stream: true で両方が解消するが、tok/s 計測 (usage) と
reasoning_content フォールバックを壊していないことを保証する必要がある。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import llmbench.clients.openai_compat as oc
from llmbench.clients.openai_compat import OpenAICompatClient

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------- テスト用のレスポンスモック ----------

class _FakeStreamResp:
    """SSE を返すレスポンスのモック. close() が呼ばれたかも記録する."""

    def __init__(self, lines, status=200, headers=None):
        self._lines = lines
        self.status_code = status
        self.reason = "OK"
        self.text = ""
        self.headers = headers or {}
        self.closed = False

    def iter_lines(self, decode_unicode=False):
        yield from self._lines

    def close(self):
        self.closed = True


class _FakeJsonResp:
    """非ストリーム(従来)レスポンスのモック."""

    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.reason = "OK"
        self.text = ""
        self.headers = {}

    def json(self):
        return self._data


def _sse(obj) -> str:
    return "data: " + json.dumps(obj) + ""


def _delta(content=None, reasoning=None, finish_reason=None) -> str:
    d = {}
    if content is not None:
        d["content"] = content
    if reasoning is not None:
        d["reasoning_content"] = reasoning
    return _sse({"choices": [{"delta": d, "finish_reason": finish_reason}]})


def _usage_chunk(prompt=5, completion=10) -> str:
    return _sse({
        "choices": [],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    })


def _install(monkeypatch, resp):
    """requests.post を差し替え、実際に送られた payload を返り値で覗けるようにする."""
    sent = {}

    def _post(url, **kw):
        sent.update(kw.get("json") or {})
        sent["_stream_kw"] = kw.get("stream")
        sent["_timeout"] = kw.get("timeout")
        return resp

    monkeypatch.setattr(oc.requests, "post", _post)
    return sent


def _client(**overrides):
    cfg = {"base_url": "http://h/v1", "model": "x", "max_tokens": 100}
    cfg.update(overrides)
    return OpenAICompatClient("m", cfg)


# ---------- 回帰: stream 未指定なら従来どおり非ストリーム ----------

def test_default_is_non_stream(monkeypatch):
    """stream を書いていないモデル (local-openai/gemini/glm) の挙動は変わらない."""
    resp = _FakeJsonResp({
        "choices": [{"message": {"content": "--- FILE: a.py ---"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10},
    })
    sent = _install(monkeypatch, resp)
    r = _client()._post_once("sys", "user")
    assert r.text == "--- FILE: a.py ---"
    assert "stream" not in sent, "stream 未指定なのに stream を送っている"
    assert "stream_options" not in sent
    assert sent["_stream_kw"] is False


# ---------- stream: true のリクエスト内容 ----------

def test_stream_request_shape(monkeypatch):
    sent = _install(monkeypatch, _FakeStreamResp([_delta(content="x"),
                                                  _usage_chunk()]))
    _client(stream=True, timeout=2400)._post_once("sys", "user")
    assert sent["stream"] is True
    # usage を明示要求しないと completion_tokens が返らず tok/s が測れなくなる
    assert sent["stream_options"] == {"include_usage": True}
    assert sent["_stream_kw"] is True
    assert sent["_timeout"] == 2400


# ---------- SSE のパース ----------

def test_stream_concatenates_content_and_reads_usage(monkeypatch):
    _install(monkeypatch, _FakeStreamResp([
        _delta(reasoning="考え中..."),
        ": keep-alive",                  # SSEコメントは無視される
        "",                              # 空行も無視される
        "event: ping",                   # data: 以外の行も無視される
        _delta(content="--- FILE: "),
        _delta(content="a.py ---"),
        "data: {壊れたJSON",              # 壊れた行でも落ちない
        _usage_chunk(prompt=11, completion=22),
        "data: [DONE]",
    ]))
    r = _client(stream=True)._post_once("sys", "user")
    assert r.text == "--- FILE: a.py ---"
    assert r.prompt_tokens == 11
    assert r.completion_tokens == 22


def test_stream_stops_at_done(monkeypatch):
    _install(monkeypatch, _FakeStreamResp([
        _delta(content="keep"),
        "data: [DONE]",
        _delta(content="MUST-NOT-APPEAR"),
    ]))
    assert _client(stream=True)._post_once("s", "u").text == "keep"


def test_stream_tokens_per_sec_still_computable(monkeypatch):
    """tok/s はベンチの主要指標。stream でも欠測しないこと."""
    _install(monkeypatch, _FakeStreamResp([_delta(content="x"),
                                           _usage_chunk(completion=22)]))
    r = _client(stream=True).generate("s", "u")   # generate 経由で latency が入る
    assert r.completion_tokens == 22
    assert r.tokens_per_sec is not None and r.tokens_per_sec > 0


# ---------- content空 → reasoning_content フォールバック (stream版) ----------

def test_stream_falls_back_to_reasoning_content(capsys, monkeypatch):
    _install(monkeypatch, _FakeStreamResp([
        _delta(reasoning="<think>--- FILE: a.py ---"),
        _usage_chunk(completion=100),
    ]))
    r = _client(stream=True, max_tokens=100)._post_once("s", "u")
    assert r.text == "<think>--- FILE: a.py ---"
    assert "reasoning_content" in capsys.readouterr().err


# ---------- finish_reason=length の可視化 ----------

def test_length_finish_reason_warns(capsys, monkeypatch):
    """max_tokens で打ち切られたことが黙って起きないこと (今回の主因)."""
    _install(monkeypatch, _FakeStreamResp([
        _delta(content="--- FILE: a.py ---", finish_reason="length"),
        _usage_chunk(completion=100),
    ]))
    _client(stream=True, max_tokens=100)._post_once("s", "u")
    err = capsys.readouterr().err
    assert "finish_reason=length" in err
    assert "max_tokens" in err


def test_normal_finish_reason_does_not_warn(capsys, monkeypatch):
    _install(monkeypatch, _FakeStreamResp([
        _delta(content="ok", finish_reason="stop"),
        _usage_chunk(),
    ]))
    _client(stream=True)._post_once("s", "u")
    assert "finish_reason=length" not in capsys.readouterr().err


# ---------- reasoning_effort ----------

def test_reasoning_effort_omitted_by_default(monkeypatch):
    """未指定ならキー自体を送らない (サーバ既定 xhigh のまま計測する)."""
    sent = _install(monkeypatch, _FakeStreamResp([_delta(content="x"),
                                                  _usage_chunk()]))
    _client(stream=True)._post_once("s", "u")
    assert "reasoning_effort" not in sent


def test_reasoning_effort_passed_when_set(monkeypatch):
    sent = _install(monkeypatch, _FakeStreamResp([_delta(content="x"),
                                                  _usage_chunk()]))
    _client(stream=True, reasoning_effort="medium")._post_once("s", "u")
    assert sent["reasoning_effort"] == "medium"


# ---------- 接続の後始末とリトライ ----------

def test_stream_response_is_closed(monkeypatch):
    """ストリームは明示 close しないと接続が残る."""
    resp = _FakeStreamResp([_delta(content="x"), _usage_chunk()])
    _install(monkeypatch, resp)
    _client(stream=True)._post_once("s", "u")
    assert resp.closed is True


def test_stream_response_closed_even_on_http_error(monkeypatch):
    resp = _FakeStreamResp([], status=400)
    _install(monkeypatch, resp)
    with pytest.raises(RuntimeError, match="400"):
        _client(stream=True)._post_once("s", "u")
    assert resp.closed is True


# ---------- 429 / 5xx のリトライ (--concurrency >1 で必須) ----------

@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_status_is_retried(status, monkeypatch):
    """レート制限・ゲートウェイ一時障害は時間を置けば直るので retry する."""
    calls = {"n": 0}
    ok = _FakeStreamResp([_delta(content="recovered"), _usage_chunk()])

    def _post(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeStreamResp([], status=status)
        return ok

    monkeypatch.setattr(oc.requests, "post", _post)
    c = _client(stream=True, transient_retries=2, transient_backoff=0)
    assert c._generate("s", "u").text == "recovered"
    assert calls["n"] == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_non_retryable_status_fails_immediately(status, monkeypatch):
    """投げ直しても直らないエラーで3時間のランを溶かさない."""
    calls = {"n": 0}

    def _post(url, **kw):
        calls["n"] += 1
        return _FakeStreamResp([], status=status)

    monkeypatch.setattr(oc.requests, "post", _post)
    with pytest.raises(RuntimeError, match=str(status)):
        _client(stream=True, transient_retries=2, transient_backoff=0)._generate(
            "s", "u"
        )
    assert calls["n"] == 1, "リトライ不能なエラーを retry している"


def test_retry_after_header_overrides_backoff(monkeypatch):
    """429 が Retry-After を返したらバックオフより優先する."""
    slept = []
    monkeypatch.setattr(oc.time, "sleep", slept.append)
    calls = {"n": 0}
    ok = _FakeStreamResp([_delta(content="ok"), _usage_chunk()])

    def _post(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeStreamResp([], status=429, headers={"Retry-After": "7"})
        return ok

    monkeypatch.setattr(oc.requests, "post", _post)
    _client(stream=True, transient_retries=2, transient_backoff=99)._generate("s", "u")
    assert slept == [7.0], f"Retry-After が使われていない: {slept}"


def test_absurd_retry_after_is_capped(monkeypatch):
    """Retry-After に巨大値が来てもランを止めない."""
    slept = []
    monkeypatch.setattr(oc.time, "sleep", slept.append)
    calls = {"n": 0}
    ok = _FakeStreamResp([_delta(content="ok"), _usage_chunk()])

    def _post(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeStreamResp([], status=429, headers={"Retry-After": "99999"})
        return ok

    monkeypatch.setattr(oc.requests, "post", _post)
    _client(stream=True, transient_retries=2, transient_backoff=1)._generate("s", "u")
    assert slept == [oc._MAX_RETRY_AFTER]


def test_malformed_retry_after_falls_back_to_backoff(monkeypatch):
    """HTTP-date 形式や不正値でも落ちず、指数バックオフに戻る."""
    slept = []
    monkeypatch.setattr(oc.time, "sleep", slept.append)
    calls = {"n": 0}
    ok = _FakeStreamResp([_delta(content="ok"), _usage_chunk()])

    def _post(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeStreamResp(
                [], status=429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
            )
        return ok

    monkeypatch.setattr(oc.requests, "post", _post)
    _client(stream=True, transient_retries=2, transient_backoff=3)._generate("s", "u")
    assert slept == [3.0]


def test_transient_retry_works_with_stream(monkeypatch):
    """Connection reset の単発でタスクを落とさない (transient_retries の回帰)."""
    calls = {"n": 0}
    ok = _FakeStreamResp([_delta(content="recovered"), _usage_chunk()])

    def _post(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise oc.requests.exceptions.ConnectionError(
                "('Connection aborted.', ConnectionResetError(54, ...))"
            )
        return ok

    monkeypatch.setattr(oc.requests, "post", _post)
    c = _client(stream=True, transient_retries=2, transient_backoff=0)
    assert c._generate("s", "u").text == "recovered"
    assert calls["n"] == 2


# ---------- runner: 生成失敗時に経過時間を落とさない ----------

def test_generation_error_records_elapsed_time():
    """タイムアウト失敗が (0.0s) と表示され原因追跡を妨げていた件の回帰."""
    import time as _time

    from llmbench.runner import BenchmarkRunner

    class _SlowFailClient:
        def generate(self, system, user):
            _time.sleep(0.05)
            raise oc.requests.exceptions.Timeout("Read timed out. (read timeout=600)")

    r = BenchmarkRunner({}, Path("tasks"))
    at = r._one_attempt(_SlowFailClient(), None, "sys", "user", None, None, 0)
    assert at.resolved is False
    assert "generation error" in at.fail_reason
    assert at.latency_sec > 0, "生成失敗時に経過時間が記録されていない"


# ---------- config.yaml の設定そのものの回帰 ----------

def test_qwen_coding_config_is_consistent():
    """qwen3.8-max (思考モデル) を timeout で殺さない設定になっているか."""
    cfg = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    q = cfg["models"]["qwen-coding"]
    assert q["stream"] is True, "非ストリームだと read timeout が生成全体に効く"
    assert q["transient_retries"] >= 1, "0 だと単発の reset でタスクが死ぬ"
    # 実測スループットの下限 (43 tok/s) で max_tokens を出し切れる時間があるか
    slowest_tok_per_sec = 43
    need = q["max_tokens"] / slowest_tok_per_sec
    assert q["timeout"] > need, (
        f"timeout={q['timeout']}s では max_tokens={q['max_tokens']} を "
        f"{slowest_tok_per_sec}tok/s で出し切れない (必要 約{need:.0f}s)"
    )


def test_sample_temp_is_not_wildly_off_production():
    """runs>1 で temperature が差し替わる。実運用(0.2)から離れすぎないこと."""
    run_cfg = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())["run"]
    assert 0.2 <= run_cfg["sample_temp"] <= 0.5, (
        f"sample_temp={run_cfg['sample_temp']} は実運用 temperature=0.2 から遠い。"
        "pass@k の多様性と実運用の再現性のバランスを取ること"
    )


def test_generate_retries_controls_regeneration():
    """--generate-retries 0 でパース失敗時の再生成が起きないこと."""
    from llmbench.clients.base import GenerationResult
    from llmbench.runner import BenchmarkRunner

    class _CountingClient:
        def __init__(self):
            self.n = 0

        def generate(self, system, user):
            self.n += 1
            return GenerationResult(
                text="パースできない出力", latency_sec=0.01, completion_tokens=1
            )

    class _AlwaysParseFailGrader:
        def evaluate(self, task, text, ctx):
            class _Ev:
                parse_ok = False
                resolved = False
                quality_score = 0.0
                parse_error = "FILEブロックが無い"
                parsed_files: dict = {}
                fail_reason = "parse失敗"
                detail_output = ""
                components: dict = {}
            return _Ev()

    r = BenchmarkRunner({}, Path("tasks"))
    c0 = _CountingClient()
    r._one_attempt(c0, _AlwaysParseFailGrader(), "s", "u", None, None, 0)
    c1 = _CountingClient()
    r._one_attempt(c1, _AlwaysParseFailGrader(), "s", "u", None, None, 1)
    assert c0.n == 1, "retries=0 なのに再生成している"
    assert c1.n == 2, "retries=1 で再生成されていない"
