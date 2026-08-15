"""打ち切り (max_tokens 到達) の検出・伝播とサンプリング設定送信の回帰テスト.

背景:
  * 実測 L7 のラン: 失敗39件のうち20件が max_tokens 上限起因だった。
    それが results.json のどこにも残らず「解けなかった」と同じ見た目に
    なっていたため、モデルの実力と読まれてしまっていた。
  * ``finish_reason=length`` の警告に ``content.strip()`` の条件が付いており、
    **content が空 = 最も危険な場面で警告が出ない**状態だった。
  * ``top_p`` / ``top_k`` / ``min_p`` / ``seed`` は payload に一度も載って
    おらず、llama-server 既定の ``seed=-1`` (毎回ランダム) で測っていた。
"""

from __future__ import annotations

import json
from pathlib import Path

import llmbench.clients.openai_compat as oc
from llmbench.clients import SAMPLING_KEYS, create_client, sampling_of
from llmbench.clients.base import GenerationResult
from llmbench.clients.openai_compat import OpenAICompatClient
from llmbench.runner import (
    Attempt,
    BenchmarkRunner,
    RunResult,
    TaskResult,
    _aggregate_attempts,
    _extraction_suspect,
    save_run,
)

# ────────────────── モック ──────────────────

class _FakeJsonResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.reason = "OK"
        self.text = ""
        self.headers = {}

    def json(self):
        return self._data


class _FakeStreamResp:
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200
        self.reason = "OK"
        self.text = ""
        self.headers = {}
        self.closed = False

    def iter_lines(self, decode_unicode=False):
        yield from self._lines

    def close(self):
        self.closed = True


def _install(monkeypatch, resp):
    sent = {}

    def _post(url, **kw):
        sent.update(kw.get("json") or {})
        return resp

    monkeypatch.setattr(oc.requests, "post", _post)
    return sent


def _client(**overrides):
    cfg = {"base_url": "http://h/v1", "model": "x", "max_tokens": 100}
    cfg.update(overrides)
    return OpenAICompatClient("m", cfg)


def _chat(message, finish_reason="stop", completion_tokens=10):
    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 5, "completion_tokens": completion_tokens},
    }


# ────────────────── ① finish_reason / truncated ──────────────────

def test_finish_reason_length_marks_truncated(monkeypatch):
    _install(monkeypatch, _FakeJsonResp(
        _chat({"content": "--- FILE: a.py ---"}, finish_reason="length")))
    r = _client()._post_once("s", "u")
    assert r.finish_reason == "length"
    assert r.truncated is True
    assert r.max_tokens == 100


def test_finish_reason_stop_is_not_truncated(monkeypatch):
    _install(monkeypatch, _FakeJsonResp(_chat({"content": "ok"})))
    r = _client()._post_once("s", "u")
    assert r.truncated is False
    assert r.finish_reason == "stop"


def test_completion_tokens_reaching_max_tokens_marks_truncated(monkeypatch):
    """finish_reason を返さないサーバでも、上限到達なら打ち切り扱いにする."""
    _install(monkeypatch, _FakeJsonResp(
        _chat({"content": "x"}, finish_reason=None, completion_tokens=100)))
    r = _client(max_tokens=100)._post_once("s", "u")
    assert r.truncated is True


def test_length_warning_fires_even_when_content_is_empty(capsys, monkeypatch):
    """旧実装は content.strip() を条件にしていたため空のとき黙っていた."""
    _install(monkeypatch, _FakeJsonResp(
        _chat({"content": "", "reasoning_content": ""},
              finish_reason="length", completion_tokens=100)))
    r = _client(max_tokens=100)._post_once("s", "u")
    err = capsys.readouterr().err
    assert "finish_reason=length" in err
    assert r.truncated is True
    assert r.text == ""


def test_reasoning_fallback_is_kept_but_marked_truncated(capsys, monkeypatch):
    """フォールバックは残す。ただし打ち切り扱い + 信頼できない旨を出す."""
    _install(monkeypatch, _FakeJsonResp(
        _chat({"content": "", "reasoning_content": "--- FILE: a.py ---"},
              finish_reason=None, completion_tokens=10)))
    r = _client()._post_once("s", "u")
    assert r.text == "--- FILE: a.py ---"      # 既存挙動 (救出) は維持
    assert r.truncated is True
    err = capsys.readouterr().err
    assert "reasoning_content" in err
    assert "信頼できない" in err
    assert "予算内に完了しておらず" in err


def test_stream_propagates_finish_reason_and_truncated(monkeypatch):
    lines = [
        "data: " + json.dumps({"choices": [{"delta": {"content": "code"},
                                            "finish_reason": "length"}]}),
        "data: " + json.dumps({"choices": [],
                               "usage": {"prompt_tokens": 1,
                                         "completion_tokens": 100}}),
        "data: [DONE]",
    ]
    _install(monkeypatch, _FakeStreamResp(lines))
    r = _client(stream=True, max_tokens=100)._post_once("s", "u")
    assert r.finish_reason == "length"
    assert r.truncated is True
    assert r.max_tokens == 100


def test_generation_result_defaults_are_backward_compatible():
    """既存の呼び出し (text だけ) が壊れないこと."""
    g = GenerationResult(text="x")
    assert g.finish_reason is None
    assert g.truncated is False
    assert g.max_tokens is None


# ────────────────── ② サンプリング設定の送信 ──────────────────

def test_sampling_params_not_sent_when_unset(monkeypatch):
    sent = _install(monkeypatch, _FakeJsonResp(_chat({"content": "x"})))
    _client()._post_once("s", "u")
    for key in ("top_p", "top_k", "min_p", "seed"):
        assert key not in sent, f"未指定なのに {key} を送っている"


def test_sampling_params_sent_when_set(monkeypatch):
    sent = _install(monkeypatch, _FakeJsonResp(_chat({"content": "x"})))
    _client(top_p=0.8, top_k=20, min_p=0.05, seed=1234)._post_once("s", "u")
    assert sent["top_p"] == 0.8
    assert sent["top_k"] == 20
    assert sent["min_p"] == 0.05
    assert sent["seed"] == 1234


def test_seed_zero_is_sent(monkeypatch):
    """0 は「未指定」ではない (top_k=0 / seed=0 は意味のある値)."""
    sent = _install(monkeypatch, _FakeJsonResp(_chat({"content": "x"})))
    _client(seed=0, top_k=0)._post_once("s", "u")
    assert sent["seed"] == 0
    assert sent["top_k"] == 0


def test_create_client_applies_sampling_defaults():
    cfg = {"type": "openai", "base_url": "http://h/v1", "model": "x",
           "temperature": 0.2}
    c = create_client("m", cfg, defaults={"seed": 7, "top_p": 0.9,
                                          "temperature": 0.9})
    assert c.seed == 7
    assert c.top_p == 0.9
    assert c.temperature == 0.2       # models 側の指定が優先
    assert cfg.get("seed") is None    # 呼び出し元の dict を壊さない


def test_create_client_without_defaults_is_unchanged():
    c = create_client("m", {"type": "openai", "base_url": "http://h/v1",
                            "model": "x"})
    assert c.seed is None and c.top_p is None and c.top_k is None


def test_sampling_of_reports_effective_values_and_reproducibility():
    c = _client(seed=None)
    c.temperature = 0.8               # runs>1 の実行時上書きを模す
    s = sampling_of(c)
    assert set(SAMPLING_KEYS) <= set(s)
    assert s["temperature"] == 0.8
    assert s["reproducible"] is False
    c.seed = 42
    assert sampling_of(c)["reproducible"] is True


# ────────────────── ③ runner への伝播 ──────────────────

def _attempt(truncated=False, resolved=False, finish_reason=""):
    return Attempt(resolved=resolved, truncated=truncated,
                   finish_reason=finish_reason, max_tokens=24576,
                   latency_sec=1.0)


def test_aggregate_attempts_records_truncation():
    tr = TaskResult(task_id="t1", difficulty="easy")
    _aggregate_attempts(tr, [_attempt(truncated=True, finish_reason="length"),
                             _attempt()], {})
    assert tr.truncated is True
    assert tr.n_truncated == 1
    assert tr.max_tokens == 24576
    assert tr.attempts[0]["truncated"] is True
    assert tr.attempts[0]["finish_reason"] == "length"


def test_aggregate_attempts_without_truncation():
    tr = TaskResult(task_id="t1", difficulty="easy")
    _aggregate_attempts(tr, [_attempt(), _attempt()], {})
    assert tr.truncated is False and tr.n_truncated == 0


def test_save_run_writes_truncation_and_sampling(tmp_path):
    run = RunResult(model="m", issue_lang="en")
    tr = TaskResult(task_id="t1", difficulty="easy", truncated=True,
                    n_truncated=2, finish_reason="length", max_tokens=49152)
    run.results = [tr, TaskResult(task_id="t2", difficulty="easy")]
    run.environment = {"execution": "local",
                       "sampling": {"temperature": 0.2, "seed": None,
                                    "reproducible": False}}
    json_path, _ = save_run(run, tmp_path)
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert payload["summary"]["n_truncated"] == 1
    row = payload["results"][0]
    assert row["truncated"] is True
    assert row["finish_reason"] == "length"
    assert row["max_tokens"] == 49152
    assert payload["environment"]["sampling"]["reproducible"] is False


# ────────────────── ④ 再生成ゲート ──────────────────

class _Ev:
    def __init__(self, parse_ok, parse_error="", parse_warnings=None):
        self.parse_ok = parse_ok
        self.parse_error = parse_error
        self.parse_warnings = parse_warnings or []
        self.resolved = False
        self.quality_score = 0.0
        self.parsed_files = {}
        self.fail_reason = ""
        self.detail_output = ""
        self.components = {}


def test_extraction_suspect_flags_warnings_and_errors():
    assert _extraction_suspect(_Ev(True)) is False
    assert _extraction_suspect(_Ev(True, parse_warnings=["placeholder"])) is True
    assert _extraction_suspect(_Ev(False, parse_error="no file blocks")) is True


class _CountingClient:
    """呼ばれた回数を数えるだけのクライアント."""

    def __init__(self):
        self.calls = 0

    def generate(self, system, user):
        self.calls += 1
        return GenerationResult(text="x", latency_sec=0.1, truncated=True,
                                finish_reason="length", max_tokens=100)


class _Grader:
    def __init__(self, ev):
        self.ev = ev

    def evaluate(self, task, text, ctx):
        return self.ev


def _runner():
    return BenchmarkRunner({}, Path("."))


def test_regeneration_gate_retries_on_suspect_extraction():
    """parse_ok=True でも警告付きなら作り直す。ただし retries 回で必ず抜ける."""
    r = _runner()
    client = _CountingClient()
    grader = _Grader(_Ev(True, parse_warnings=["placeholder path dropped"]))
    at = r._one_attempt(client, grader, "s", "u", None, None, retries=2)
    assert client.calls == 3          # 1 + retries、無限ループしない
    assert at.truncated is True
    assert at.finish_reason == "length"
    assert at.max_tokens == 100


def test_regeneration_gate_stops_on_clean_extraction():
    r = _runner()
    client = _CountingClient()
    at = r._one_attempt(client, _Grader(_Ev(True)), "s", "u", None, None,
                        retries=2)
    assert client.calls == 1
    assert at.parse_ok is True


def test_regeneration_gate_retries_on_parse_failure():
    r = _runner()
    client = _CountingClient()
    at = r._one_attempt(client, _Grader(_Ev(False, parse_error="no blocks")),
                        "s", "u", None, None, retries=1)
    assert client.calls == 2
    assert at.parse_ok is False
