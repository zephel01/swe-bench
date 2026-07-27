"""推論(thinking)系モデル対策: content空 → reasoning_contentフォールバック/診断ログの単体テスト.

実サーバは使わず、requests.post をモックして OpenAICompatClient._post_once の
挙動(text選択・警告メッセージ)だけを検証する。
"""

from __future__ import annotations

import llmbench.clients.openai_compat as oc
from llmbench.clients.openai_compat import OpenAICompatClient


class _FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.reason = "OK"
        self.text = ""

    def json(self):
        return self._data


def _client(max_tokens=100, monkeypatch=None):
    return OpenAICompatClient(
        "m", {"base_url": "http://h/v1", "model": "x", "max_tokens": max_tokens}
    )


def _mock_post(data):
    def _post(url, **kw):
        return _FakeResp(data)
    return _post


def _chat_response(message, completion_tokens=10):
    return {
        "choices": [{"message": message}],
        "usage": {"prompt_tokens": 5, "completion_tokens": completion_tokens},
    }


# ---------- 通常系: contentがあればそのまま使う ----------

def test_normal_content_used_as_is(monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response({"content": "--- FILE: a.py ---"})),
    )
    c = _client()
    r = c._post_once("sys", "user")
    assert r.text == "--- FILE: a.py ---"


# ---------- content空 + reasoning_contentに答えらしきものがある → フォールバック ----------

def test_empty_content_falls_back_to_reasoning_content(capsys, monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response({
            "content": "",
            "reasoning_content": "<think>...--- FILE: a.py ---...</think>",
        }, completion_tokens=50)),
    )
    c = _client(max_tokens=100)
    r = c._post_once("sys", "user")
    assert r.text == "<think>...--- FILE: a.py ---...</think>"
    assert "reasoning_content" in capsys.readouterr().err


def test_empty_content_falls_back_to_reasoning_alt_key(monkeypatch):
    # 一部サーバは reasoning_content でなく reasoning キーを使う
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response({
            "content": "",
            "reasoning": "partial thought",
        })),
    )
    c = _client()
    r = c._post_once("sys", "user")
    assert r.text == "partial thought"


# ---------- content空 + reasoningも空 + max_tokens到達 → 「予算切れ」警告 ----------

def test_empty_all_at_max_tokens_warns_budget_exhausted(capsys, monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response(
            {"content": "", "reasoning_content": ""}, completion_tokens=100,
        )),
    )
    c = _client(max_tokens=100)
    r = c._post_once("sys", "user")
    assert r.text == ""
    err = capsys.readouterr().err
    assert "max_tokens" in err
    assert "予算内に" in err


# ---------- content空 + reasoningも空 + max_tokens未到達 → 「早期停止」警告 ----------

def test_empty_all_under_max_tokens_warns_early_stop(capsys, monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response(
            {"content": "", "reasoning_content": ""}, completion_tokens=12,
        )),
    )
    c = _client(max_tokens=100)
    r = c._post_once("sys", "user")
    assert r.text == ""
    err = capsys.readouterr().err
    assert "早期に停止" in err
    assert "completion_tokens=12" in err


def test_completion_tokens_still_reported_on_empty(monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response({"content": ""}, completion_tokens=24576)),
    )
    c = _client(max_tokens=24576)
    r = c._post_once("sys", "user")
    assert r.completion_tokens == 24576


def test_whitespace_only_content_treated_as_empty(monkeypatch):
    monkeypatch.setattr(
        oc.requests, "post",
        _mock_post(_chat_response({"content": "   \n  "})),
    )
    c = _client()
    r = c._post_once("sys", "user")
    assert r.text == ""
