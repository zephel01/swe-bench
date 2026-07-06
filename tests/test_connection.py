"""接続先解決ロジックの単体テスト (ネットワーク不要・全てモック)."""

from __future__ import annotations

from pathlib import Path

import pytest

from llmbench.clients.base import expand_env
from llmbench.clients.ollama import OllamaClient
from llmbench.clients.openai_compat import OpenAICompatClient, fetch_served_model
from llmbench.runner import BenchmarkRunner


# ---------- expand_env ----------

def test_expand_env_passthrough():
    assert expand_env("literal") == "literal"
    assert expand_env(123) == 123
    assert expand_env(None) is None


def test_expand_env_set(monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret")
    assert expand_env("${MY_KEY}") == "secret"
    assert expand_env("$MY_KEY") == "secret"


def test_expand_env_unset_raises(monkeypatch):
    monkeypatch.delenv("MY_KEY", raising=False)
    with pytest.raises(ValueError, match="MY_KEY"):
        expand_env("${MY_KEY}", where="models.x.api_key")


# ---------- OpenAICompatClient ----------

def test_openai_missing_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="base_url"):
        OpenAICompatClient("m", {"model": "x"})


def test_openai_base_url_env_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://envhost:9/v1")
    c = OpenAICompatClient("m", {"model": "x"})
    assert c.base_url == "http://envhost:9/v1"


def test_openai_config_beats_env(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://envhost:9/v1")
    c = OpenAICompatClient(
        "m", {"base_url": "http://cfg:1/v1/", "model": "x"}
    )
    assert c.base_url == "http://cfg:1/v1"


def test_openai_api_key_unset_env_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAICompatClient(
            "ref", {"base_url": "http://h/v1", "model": "x",
                    "api_key": "${OPENAI_API_KEY}"},
        )


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _fake_models_get(models):
    def _get(url, **kw):
        return _FakeResp({"data": [{"id": m} for m in models]})
    return _get


def test_auto_picks_first(monkeypatch):
    import llmbench.clients.openai_compat as oc
    monkeypatch.setattr(oc.requests, "get", _fake_models_get(["a-model", "b"]))
    c = OpenAICompatClient("m", {"base_url": "http://h/v1", "model": "auto"})
    assert c.model == "a-model"


def test_auto_prefer_substring(monkeypatch):
    import llmbench.clients.openai_compat as oc
    monkeypatch.setattr(
        oc.requests, "get", _fake_models_get(["llama-3", "Qwen2.5-Coder"])
    )
    c = OpenAICompatClient(
        "m", {"base_url": "http://h/v1", "model": "auto",
              "auto_prefer": "qwen"},
    )
    assert c.model == "Qwen2.5-Coder"


def test_auto_prefer_no_match_raises(monkeypatch):
    import llmbench.clients.openai_compat as oc
    monkeypatch.setattr(oc.requests, "get", _fake_models_get(["llama-3"]))
    with pytest.raises(ValueError, match="auto_prefer"):
        OpenAICompatClient(
            "m", {"base_url": "http://h/v1", "model": "auto",
                  "auto_prefer": "qwen"},
        )


def test_fetch_served_model_empty_raises(monkeypatch):
    import llmbench.clients.openai_compat as oc
    monkeypatch.setattr(oc.requests, "get", _fake_models_get([]))
    with pytest.raises(RuntimeError):
        fetch_served_model("http://h/v1")


# ---------- OllamaClient ----------

def test_ollama_missing_model_friendly(monkeypatch):
    with pytest.raises(ValueError, match="model"):
        OllamaClient("o", {"base_url": "http://h"})


def test_ollama_env_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://remote:11434")
    c = OllamaClient("o", {"model": "m"})
    assert c.base_url == "http://remote:11434"


def test_ollama_config_beats_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://remote:11434")
    c = OllamaClient("o", {"model": "m", "base_url": "http://cfg:1/"})
    assert c.base_url == "http://cfg:1"


# ---------- BenchmarkRunner: ollama_host 優先順 ----------

def _runner(config):
    return BenchmarkRunner(config, Path("tasks"))


def test_ollama_host_priority(monkeypatch):
    cfg_model = {"models": {"lo": {"type": "ollama", "base_url": "http://cfg:1"}}}
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    # run.ollama_host が最優先
    r = _runner({**cfg_model, "run": {"ollama_host": "http://cli:1"}})
    assert r.ollama_host() == "http://cli:1"
    # env が config モデルより優先
    monkeypatch.setenv("OLLAMA_HOST", "http://env:1")
    assert _runner(cfg_model).ollama_host() == "http://env:1"
    # env なし → configモデル
    monkeypatch.delenv("OLLAMA_HOST")
    assert _runner(cfg_model).ollama_host() == "http://cfg:1"
    # 何もなし → 既定
    assert _runner({}).ollama_host() == "http://localhost:11434"


# ---------- BenchmarkRunner: resolve_model ----------

def test_resolve_base_url_override():
    r = _runner({"models": {"lo": {"type": "openai",
                                   "base_url": "http://cfg:1/v1",
                                   "model": "x"}}})
    cfg = r.resolve_model("lo", base_url="http://override:2/v1")
    assert cfg["base_url"] == "http://override:2/v1"
    # 元のconfigは破壊しない
    assert r.config["models"]["lo"]["base_url"] == "http://cfg:1/v1"


def test_resolve_client_type_synthesis():
    r = _runner({})
    cfg = r.resolve_model("auto", client_type="openai",
                          base_url="http://llamacpp:8085/v1")
    assert cfg == {"type": "openai", "base_url": "http://llamacpp:8085/v1",
                   "model": "auto"}
    cfg2 = r.resolve_model("router", client_type="multiagent",
                           base_url="http://coderouter:8088")
    assert cfg2["type"] == "multiagent"
    assert cfg2["base_url"] == "http://coderouter:8088"


def test_resolve_client_type_ollama_uses_base_url():
    r = _runner({})
    cfg = r.resolve_model("qwen:7b", client_type="ollama",
                          base_url="http://remote:11434")
    assert cfg["type"] == "ollama"
    assert cfg["base_url"] == "http://remote:11434"
    assert cfg["model"] == "qwen:7b"


def test_resolve_ollama_autodetect_uses_base_url(monkeypatch):
    import llmbench.runner as rn
    seen = {}

    def fake_list(host, **kw):
        seen["host"] = host
        return ["qwen:7b"]

    monkeypatch.setattr(rn, "list_ollama_models", fake_list)
    r = _runner({})
    cfg = r.resolve_model("qwen:7b", base_url="http://remote:11434")
    assert seen["host"] == "http://remote:11434"
    assert cfg["base_url"] == "http://remote:11434"


def test_resolve_unknown_raises(monkeypatch):
    import llmbench.runner as rn
    monkeypatch.setattr(rn, "list_ollama_models", lambda h, **k: ["other"])
    r = _runner({})
    with pytest.raises(ValueError, match="未インストール"):
        r.resolve_model("nope")


# ---------- reviewer_model の統一解決 ----------

def test_reviewer_resolves_via_ollama_autodetect(monkeypatch):
    import llmbench.runner as rn
    monkeypatch.setattr(rn, "list_ollama_models", lambda h, **k: ["rev:7b"])
    r = _runner({
        "quality": {"llm_review": {"enabled": True,
                                   "reviewer_model": "rev:7b"}},
    })
    reviewer = r._make_reviewer()
    assert reviewer is not None
    assert reviewer.model == "rev:7b"


def test_reviewer_unresolvable_message(monkeypatch):
    import llmbench.runner as rn
    monkeypatch.setattr(rn, "list_ollama_models", lambda h, **k: [])
    r = _runner({
        "quality": {"llm_review": {"enabled": True,
                                   "reviewer_model": "ghost"}},
    })
    with pytest.raises(ValueError, match="reviewer_model 'ghost'"):
        r._make_reviewer()


def test_reviewer_disabled_returns_none():
    assert _runner({})._make_reviewer() is None
