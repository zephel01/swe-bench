"""サブスクCLIクライアント (type: cli) の単体テスト.

実CLI (claude / codex / grok) は使わず、Python ワンライナーの偽CLIで
コマンド組み立て・プロンプト受け渡し・出力パース・異常系を検証する。
"""

from __future__ import annotations

import sys

import pytest

from llmbench.clients import create_client
from llmbench.clients.cli_agent import CliAgentClient

PY = sys.executable


def _cli(cfg: dict, name: str = "sub") -> CliAgentClient:
    return CliAgentClient(name, {"type": "cli", **cfg})


# ---------- 生成 (custom / stdout) ----------

def test_custom_arg_prompt_stdout():
    c = _cli({
        "preset": "custom",
        "command": [PY, "-c", "import sys; print('echo:' + sys.argv[-1])"],
    })
    r = c.generate("SYS", "hello")
    # system は user に前置される
    assert r.text == "echo:SYS\n\nhello"
    assert r.latency_sec > 0


def test_custom_stdin_prompt():
    c = _cli({
        "preset": "custom",
        "prompt_via": "stdin",
        "command": [PY, "-c", "import sys; print(sys.stdin.read().upper())"],
    })
    r = c.generate("", "hi")
    assert r.text == "HI"


def test_create_client_dispatch():
    c = create_client("sub", {
        "type": "cli", "preset": "custom",
        "command": [PY, "-c", "print('x')"],
    })
    assert isinstance(c, CliAgentClient)


# ---------- claude プリセット (JSON パース) ----------

_FAKE_CLAUDE = (
    "import sys, json;"
    "p = sys.stdin.read();"
    "print(json.dumps({'type': 'result', 'is_error': False,"
    " 'result': 'patched: ' + p[:10],"
    " 'usage': {'input_tokens': 7, 'output_tokens': 42}}))"
)


def test_claude_json_parse():
    c = _cli({
        "preset": "claude",
        "command": [PY, "-c", _FAKE_CLAUDE],  # command でCLI本体だけ差し替え
    })
    assert c.prompt_via == "stdin" and c.parse_mode == "claude_json"
    r = c.generate("", "fix the bug")
    assert r.text.startswith("patched: fix the bu")
    assert r.prompt_tokens == 7
    assert r.completion_tokens == 42


def test_claude_json_is_error_raises():
    c = _cli({
        "preset": "claude",
        "command": [PY, "-c",
                    "import json;"
                    "print(json.dumps({'is_error': True,"
                    " 'result': 'rate limit reached'}))"],
    })
    with pytest.raises(RuntimeError, match="rate limit"):
        c.generate("", "x")


def test_claude_non_json_falls_back_to_stdout():
    c = _cli({
        "preset": "claude",
        "command": [PY, "-c", "print('plain text output')"],
    })
    assert c.generate("", "x").text == "plain text output"


# ---------- codex プリセット (--output-last-message) ----------

_FAKE_CODEX = (
    "import sys, pathlib;"
    "i = sys.argv.index('--output-last-message');"
    "pathlib.Path(sys.argv[i + 1]).write_text('final answer');"
    "print('thinking... noise ...')"
)


def test_codex_last_message_file():
    c = _cli({
        "preset": "codex",
        "command": [PY, "-c", _FAKE_CODEX],
    })
    assert c.parse_mode == "last_message_file"
    r = c.generate("", "task")
    assert r.text == "final answer"       # stdoutのノイズではなくファイルを採用


def test_codex_missing_file_falls_back_to_stdout():
    c = _cli({
        "preset": "codex",
        "command": [PY, "-c", "print('stdout only')"],
    })
    assert c.generate("", "task").text == "stdout only"


# ---------- コマンド組み立て ----------

def test_model_flag_and_extra_args():
    c = _cli({
        "preset": "claude",
        "model": "sonnet",
        "extra_args": ["--max-turns", "3"],
    })
    argv = c.build_argv("PROMPT", None)
    assert argv[:4] == ["claude", "-p", "--output-format", "json"]
    assert ["--model", "sonnet"] == argv[4:6]
    assert ["--max-turns", "3"] == argv[6:8]
    assert "PROMPT" not in argv               # claude は stdin 渡し


def test_env_expansion(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "t0k")
    c = _cli({
        "preset": "custom",
        "command": [PY, "-c",
                    "import os; print(os.environ['INJECTED'])"],
        "env": {"INJECTED": "${MY_TOKEN}"},
    })
    assert c.generate("", "x").text == "t0k"


# ---------- 異常系 ----------

def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="preset"):
        _cli({"preset": "gemini"})


def test_custom_without_command_raises():
    with pytest.raises(ValueError, match="command"):
        _cli({"preset": "custom"})


def test_missing_binary_friendly_error():
    c = _cli({"preset": "custom", "command": ["no-such-cli-xyz"]})
    with pytest.raises(ValueError, match="no-such-cli-xyz"):
        c.generate("", "x")


def test_claude_missing_binary_shows_install_hint(monkeypatch):
    import llmbench.clients.cli_agent as ca
    monkeypatch.setattr(ca.shutil, "which", lambda _: None)
    c = _cli({"preset": "claude"})
    with pytest.raises(ValueError, match="claude-code"):
        c.generate("", "x")


def test_nonzero_exit_raises_with_stderr():
    c = _cli({
        "preset": "custom",
        "command": [PY, "-c",
                    "import sys; print('usage limit', file=sys.stderr);"
                    "sys.exit(2)"],
    })
    with pytest.raises(RuntimeError, match="usage limit"):
        c.generate("", "x")


def test_timeout_raises():
    c = _cli({
        "preset": "custom",
        "timeout": 1,
        "command": [PY, "-c", "import time; time.sleep(10)"],
    })
    with pytest.raises(RuntimeError, match="タイムアウト"):
        c.generate("", "x")


def test_prompt_via_invalid_raises():
    with pytest.raises(ValueError, match="prompt_via"):
        _cli({"preset": "claude", "prompt_via": "file"})


# ---------- 実行モデルの検出 ----------

_FAKE_CLAUDE_MODELS = (
    "import sys, json;"
    "sys.stdin.read();"
    "print(json.dumps({'is_error': False, 'result': 'ok',"
    " 'usage': {'input_tokens': 1, 'output_tokens': 2},"
    " 'modelUsage': {'claude-haiku-4': {'outputTokens': 5},"
    " 'claude-sonnet-4-6': {'outputTokens': 500}}}))"
)


def test_claude_detects_model_from_model_usage(capsys):
    c = _cli({"preset": "claude", "command": [PY, "-c", _FAKE_CLAUDE_MODELS]})
    c.generate("", "x")
    assert c.detected_model == "claude-sonnet-4-6"   # 出力トークン最大を採用
    assert "実行モデル" in capsys.readouterr().err
    c.generate("", "x")                              # 同じモデルなら再表示しない
    assert "実行モデル" not in capsys.readouterr().err


def test_claude_no_model_usage_keeps_none():
    c = _cli({"preset": "claude", "command": [PY, "-c", _FAKE_CLAUDE]})
    c.generate("", "x")
    assert c.detected_model is None


def test_codex_detects_model_from_banner():
    script = (
        "import sys, pathlib;"
        "i = sys.argv.index('--output-last-message');"
        "pathlib.Path(sys.argv[i + 1]).write_text('ans');"
        "print('workdir: /tmp');print('model: gpt-5.3-codex');print('---')"
    )
    c = _cli({"preset": "codex", "command": [PY, "-c", script]})
    r = c.generate("", "x")
    assert r.text == "ans"
    assert c.detected_model == "gpt-5.3-codex"


def test_model_change_warns_again(capsys):
    c = _cli({"preset": "claude", "command": [PY, "-c", "pass"]})
    c._note_model("m-one")
    c._note_model("m-one")            # 同一モデルは無視
    c._note_model("m-two")            # 変化はあらためて警告
    err = capsys.readouterr().err
    assert err.count("🔎 実行モデル: m-one") == 1
    assert "⚠️ 実行モデルが変わりました: m-two" in err


# ---------- temperature 警告 (runs>1 の sample_temp は無視される) ----------

def test_temperature_override_warns_once(capsys):
    c = _cli({
        "preset": "custom",
        "command": [PY, "-c", "print('ok')"],
    })
    c.temperature = 0.8          # runner が runs>1 で行う上書きを再現
    c.generate("", "x")
    c.generate("", "x")
    err = capsys.readouterr().err
    assert err.count("temperature を制御できません") == 1
