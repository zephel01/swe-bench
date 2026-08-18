"""思考(reasoning)暴走ガードと fail-fast の単体テスト (ネットワーク不要).

背景 — 実測で起きたこと:
  Qwen3.8-9B (GGUF, thinking) を `--runs 5` で回すと t033 (frontier) で
  content が空のまま reasoning_content だけが伸び続け、
  max_tokens=49,152 に張り付いたまま試行が終わらなくなった。
  1試行 ≒ 150秒 × generate_retries=1 の再生成 × runs=5 = 1タスク25分。
  frontier 帯が28タスク続くのでランが実質止まって見える。

ここで守りたい性質は3つ:
  1. 縮退ループを **本文が出る前に限って** 検出し、接続を切ること
  2. 本文を書き始めた生成は絶対に打ち切らないこと (正常な長考を殺さない)
  3. 打ち切った試行は再生成せず、残りの runs もスキップすること
"""

from __future__ import annotations

import json
from pathlib import Path

import llmbench.clients.openai_compat as oc
from llmbench.clients.openai_compat import (
    FINISH_REASONING_BUDGET,
    FINISH_REASONING_LOOP,
    OpenAICompatClient,
    detect_reasoning_loop,
    duplicate_line_ratio,
    find_repeating_unit,
)
from llmbench.runner import Attempt, BenchmarkRunner, _aggregate_attempts, _hopeless


# ────────────────── ① 反復検出そのもの ──────────────────

def test_find_repeating_unit_catches_token_loop():
    """実測パターン: "1,1,1,1,..." を1行 15,434 文字."""
    assert find_repeating_unit("prefix " + "1," * 5000) == "1,"


def test_find_repeating_unit_catches_sentence_loop():
    """実測パターン: 同一文を 1,552 行."""
    line = 'If they test "Hello...World" -> hello-world. Good.\n'
    assert find_repeating_unit("intro\n" + line * 40) == line


def test_find_repeating_unit_ignores_normal_prose():
    """普通に考えている文章を反復と誤判定しない."""
    prose = (
        "Let me re-read the spec. The nested transaction should keep the outer "
        "rollback marker, so commit() on the inner scope must not clear it. "
        "I will model the stack explicitly and test the three orderings.\n"
    ) * 3
    assert find_repeating_unit(prose[:1500] + " and then something else") is None


def test_duplicate_line_ratio():
    assert duplicate_line_ratio("head\n" + "same line\n" * 30) > 0.9
    uniq = "\n".join(f"step {i}: consider case {i}" for i in range(40))
    assert duplicate_line_ratio(uniq) < 0.1
    # 行数が足りないときは判定しない
    assert duplicate_line_ratio("a\na\na\n") == 0.0


def test_detect_reasoning_loop_message():
    hit = detect_reasoning_loop("x" * 100 + "ab" * 200)
    assert hit and "反復" in hit


# ────────────────── ② ストリーム中の打ち切り ──────────────────

class _FakeStreamResp:
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200
        self.reason = "OK"
        self.text = ""
        self.headers = {}
        self.closed = False
        self.consumed = 0

    def iter_lines(self, decode_unicode=False):
        for ln in self._lines:
            self.consumed += 1
            yield ln

    def close(self):
        self.closed = True


def _sse(obj) -> str:
    return "data: " + json.dumps(obj)


def _reasoning(text: str) -> str:
    return _sse({"choices": [{"delta": {"reasoning_content": text}}]})


def _content(text: str, finish=None) -> str:
    return _sse({"choices": [{"delta": {"content": text}, "finish_reason": finish}]})


def _install(monkeypatch, resp):
    monkeypatch.setattr(oc.requests, "post", lambda url, **kw: resp)
    return resp


def _client(**overrides):
    cfg = {"base_url": "http://h/v1", "model": "x", "max_tokens": 100000,
           "stream": True}
    cfg.update(overrides)
    return OpenAICompatClient("m", cfg)


def test_loop_guard_aborts_degenerate_thinking(monkeypatch):
    """本文ゼロのまま反復し始めたら、SSE を読み切る前に接続を切る."""
    # 1チャンク500文字 × 60 = 30,000文字。ガードは 8,000文字から見始める。
    lines = [_reasoning("1," * 250) for _ in range(60)] + [_content("done", "stop")]
    resp = _install(monkeypatch, _FakeStreamResp(lines))
    r = _client()._post_once("sys", "user")

    assert r.finish_reason == FINISH_REASONING_LOOP
    assert r.truncated is True
    assert r.text == "", "縮退した思考をフォールバックで拾ってはいけない"
    assert resp.closed is True
    assert resp.consumed < len(lines), "最後まで読み切っている = 早期打ち切りできていない"


def test_loop_guard_never_aborts_after_content_started(monkeypatch):
    """本文が1文字でも出ていれば、その後どれだけ反復しても打ち切らない.

    コード生成の答えには繰り返しの多い行 (import や dict リテラル) が
    普通に出るので、ここで誤爆すると正常な生成を殺す。
    """
    lines = (
        [_content("--- FILE: a.py ---\n")]
        + [_reasoning("1," * 250) for _ in range(60)]
        + [_content("pass", "stop")]
    )
    resp = _install(monkeypatch, _FakeStreamResp(lines))
    r = _client()._post_once("sys", "user")

    assert r.finish_reason == "stop"
    assert r.truncated is False
    assert r.text.startswith("--- FILE: a.py ---")
    assert resp.consumed == len(lines)


def test_loop_guard_leaves_healthy_long_thinking_alone(monkeypatch):
    """長いだけで反復していない思考は最後まで走らせる."""
    chunks = [
        _reasoning(f"Step {i}: check invariant {i} against the spec paragraph {i}.\n")
        for i in range(600)
    ]
    _install(monkeypatch, _FakeStreamResp(chunks + [_content("ok", "stop")]))
    r = _client()._post_once("sys", "user")

    assert r.finish_reason == "stop"
    assert r.truncated is False
    assert r.text == "ok"


def test_loop_guard_can_be_disabled(monkeypatch):
    lines = [_reasoning("1," * 250) for _ in range(60)] + [_content("done", "stop")]
    resp = _install(monkeypatch, _FakeStreamResp(lines))
    r = _client(loop_guard=False)._post_once("sys", "user")

    assert r.finish_reason == "stop"
    assert resp.consumed == len(lines)


def test_reasoning_max_tokens_caps_thinking(monkeypatch):
    """反復していなくても、思考が上限に達したら切る (時間の保険)."""
    lines = [_reasoning(f"unique thought number {i}\n") for i in range(500)]
    lines.append(_content("done", "stop"))
    resp = _install(monkeypatch, _FakeStreamResp(lines))
    r = _client(loop_guard=False, reasoning_max_tokens=100)._post_once("sys", "u")

    assert r.finish_reason == FINISH_REASONING_BUDGET
    assert r.truncated is True
    assert r.text == ""
    assert resp.consumed <= 120


def test_guard_is_off_for_non_stream(monkeypatch):
    """非ストリームでは途中で切れないので、従来どおり読み切る (回帰)."""
    class _Json:
        status_code = 200
        reason = "OK"
        text = ""
        headers: dict = {}

        def json(self):
            return {
                "choices": [{"message": {"content": "",
                                         "reasoning_content": "1," * 20000},
                             "finish_reason": "length"}],
                "usage": {"completion_tokens": 100000},
            }

    _install(monkeypatch, _Json())
    r = _client(stream=False)._post_once("sys", "user")
    assert r.truncated is True
    assert r.text.startswith("1,"), "非ストリームの reasoning フォールバックは従来どおり"


# ────────────────── ③ runner 側の fail-fast ──────────────────

def test_hopeless_only_for_truncated_and_empty():
    assert _hopeless(Attempt(truncated=True, raw_output="")) is True
    assert _hopeless(Attempt(truncated=True, raw_output="   \n")) is True
    # 途中まで書けていた → 予算不足で切れただけかもしれないので回す
    assert _hopeless(Attempt(truncated=True, raw_output="--- FILE")) is False
    # 通信エラー → 時間を置けば直るので回す
    assert _hopeless(Attempt(truncated=True, errored=True)) is False
    # 単に不正解 → 当然回す
    assert _hopeless(Attempt(truncated=False, raw_output="wrong")) is False


class _HopelessClient:
    """毎回「本文ゼロで打ち切り」を返す = t033 で起きたこと."""

    def __init__(self):
        self.calls = 0

    def generate(self, system, user):
        from llmbench.clients.base import GenerationResult
        self.calls += 1
        return GenerationResult(text="", latency_sec=1.0, truncated=True,
                                finish_reason=FINISH_REASONING_LOOP,
                                max_tokens=49152)


class _Ev:
    parse_ok = False
    parse_error = "no file blocks"
    parse_warnings: list = []
    resolved = False
    quality_score = 0.0
    parsed_files: dict = {}
    fail_reason = "empty output"
    detail_output = ""
    components: dict = {}


class _Grader:
    def evaluate(self, task, text, ctx):
        return _Ev()

    def build_prompt(self, task, lang):
        return "sys", "user"


class _Task:
    task_id = "t033"
    difficulty = "frontier"
    title = "nested transaction"
    domain = "code"
    grader = "code"
    perf_timeout = None
    dir = Path(".")


def _run_task(runner, client, runs):
    import llmbench.runner as rn
    orig = rn.get_grader
    rn.get_grader = lambda name: _Grader()
    try:
        return runner._run_task(client, None, None, 1, _Task(), "en", 10, 1, runs)
    finally:
        rn.get_grader = orig


def test_fail_fast_skips_remaining_runs():
    """1回目が本文ゼロで打ち切られたら、残り4回は投げない."""
    runner = BenchmarkRunner({}, Path("."))
    client = _HopelessClient()
    tr = _run_task(runner, client, runs=5)

    assert client.calls == 1, f"fail-fast が効いていない (生成 {client.calls} 回)"
    assert tr.n_skipped == 4
    assert tr.resolved is False
    assert tr.success_rate == 0.0
    # 回していない試行を分母に入れない (測っていないものを測ったことにしない)
    assert tr.pass_k == 1
    assert tr.latency_sec == 1.0, "スキップ分を 0秒 として平均すると実測が薄まる"


def test_fail_fast_can_be_disabled():
    runner = BenchmarkRunner({"run": {"fail_fast": False}}, Path("."))
    client = _HopelessClient()
    tr = _run_task(runner, client, runs=3)

    assert client.calls == 3
    assert tr.n_skipped == 0


def test_skipped_attempts_are_excluded_from_denominator():
    from llmbench.runner import TaskResult
    tr = TaskResult(task_id="t033", difficulty="frontier", runs=5)
    attempts = [
        Attempt(resolved=False, truncated=True, latency_sec=150.0),
        *[Attempt(skipped=True, fail_reason="skipped by fail-fast") for _ in range(4)],
    ]
    _aggregate_attempts(tr, attempts, {}, k=None)

    assert tr.n_skipped == 4
    assert tr.n_errored == 0
    assert tr.success_rate == 0.0
    assert tr.n_pass == 0
    assert tr.latency_sec == 150.0
    assert "skipped by fail-fast" in tr.fail_reason
    assert [a["skipped"] for a in tr.attempts] == [False, True, True, True, True]
