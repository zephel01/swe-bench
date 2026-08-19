"""SSE の文字コード取り違えに対する回帰テスト (ネットワークはローカルループのみ).

実害 (2026-08-19): llama.cpp は `Content-Type: text/event-stream` を **charset 無し**
で返す。requests は RFC 2616 に従い `text/*` の既定を ISO-8859-1 と解釈するため、
`iter_lines(decode_unicode=True)` が UTF-8 のバイト列を latin-1 で復号していた。

被害は2段:
  1. 文字化け — 「野獣」→「éç£」。日本語は1文字が3文字に化けるので
     char_count 系のチェックが約3倍にずれる。
  2. **黙って欠落** — latin-1 復号後の文字列には U+0085 (NEL) などが現れ、
     `str.splitlines()` がそこを改行とみなして SSE 行を分断する。分断された行は
     `json.loads` に失敗し、`except json.JSONDecodeError: continue` に捨てられる。

これで `--lang ja` のランは日本語キーワード照合が全滅し、生成タスクが誤って
不合格になっていた。修正は `_consume_stream` の冒頭で `resp.encoding = "utf-8"`。
"""

from __future__ import annotations

import http.server
import json
import threading

import pytest
import requests

from llmbench.clients.openai_compat import OpenAICompatClient

# 0x85 (NEL) を含む UTF-8 列を持つ文字を必ず入れること。
# 「先」= E5 85 88 が該当し、latin-1 復号すると行が分断される。
JA = "野獣先輩、今日は暑スギィ！じゃけん冷房つけましょうね〜"


class _RecordingResp:
    """encoding を代入されたか記録するだけのモック."""

    def __init__(self, lines):
        self._lines = lines
        self.encoding = "ISO-8859-1"      # requests の既定 (charset 無しの text/*)
        self.status_code = 200
        self.reason = "OK"
        self.text = ""
        self.headers = {}

    def iter_lines(self, decode_unicode=False):
        yield from self._lines

    def close(self):
        pass


def _client(**overrides) -> OpenAICompatClient:
    cfg = {"base_url": "http://127.0.0.1:1/v1", "model": "m",
           "max_tokens": 256, "stream": True}
    cfg.update(overrides)
    return OpenAICompatClient("m", cfg)


def test_consume_stream_forces_utf8():
    """SSE を読む前に resp.encoding を utf-8 へ固定していること."""
    line = "data: " + json.dumps(
        {"choices": [{"delta": {"content": JA}, "finish_reason": "stop"}]},
        ensure_ascii=False,
    )
    resp = _RecordingResp([line, "data: [DONE]"])
    content, _reasoning, _usage, _finish, _abort = _client()._consume_stream(resp)
    assert resp.encoding == "utf-8", (
        "resp.encoding を utf-8 に固定していない。charset 無しの text/event-stream を"
        " requests が ISO-8859-1 として復号し、日本語が文字化けする"
    )
    assert content == JA


# ---------- 実際の HTTP を通した統合テスト ----------

class _SSEHandler(http.server.BaseHTTPRequestHandler):
    """llama.cpp と同じく charset を書かずに SSE を返すサーバ."""

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")   # charset 無し
        self.end_headers()
        for i in range(0, len(JA), 6):                          # 細かく分割して送る
            chunk = {"choices": [{"delta": {"content": JA[i:i + 6]}}]}
            self.wfile.write(
                b"data: " + json.dumps(chunk, ensure_ascii=False).encode("utf-8")
                + b"\n\n"
            )
        self.wfile.write(
            b"data: " + json.dumps(
                {"choices": [{"delta": {}, "finish_reason": "stop"}]}
            ).encode("utf-8") + b"\n\n"
        )
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def sse_server():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _SSEHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


def test_japanese_survives_real_sse(sse_server):
    """charset 無しの実サーバ相手でも日本語が欠けず化けないこと."""
    got = _client(base_url=sse_server).generate("sys", "user")
    assert got.text == JA, f"日本語が壊れている: {got.text!r}"
    assert len(got.text) == len(JA), (
        f"文字数がずれている ({len(got.text)} != {len(JA)})。"
        " latin-1 復号だと約3倍に膨らみ char_count 系チェックが全て狂う"
    )


def test_japanese_survives_real_sse_client(sse_server, monkeypatch):
    """クライアント経由 (base_url 差し替え) でも同じ."""
    c = _client(base_url=sse_server)
    assert c.generate("sys", "user").text == JA


def test_latin1_decoding_would_have_broken_it(sse_server):
    """修正前の挙動を再現し、確かに壊れることを固定しておく (仕様の証拠)."""
    r = requests.post(f"{sse_server}/chat/completions", json={}, stream=True)
    assert r.encoding == "ISO-8859-1", "サーバ側が charset を返してしまっている"
    out, dropped = "", 0
    for line in r.iter_lines(decode_unicode=True):      # encoding を直さない旧経路
        if not line or not line.startswith("data:"):
            continue
        body = line[5:].strip()
        if body == "[DONE]":
            break
        try:
            delta = json.loads(body)["choices"][0].get("delta") or {}
        except json.JSONDecodeError:
            dropped += 1                                 # 旧コードは黙って捨てていた
            continue
        out += delta.get("content", "")
    assert out != JA, "壊れないなら前提が変わっている。この回帰テストを見直すこと"
    assert dropped > 0, "行の分断が起きていない。NEL(0x85) を含む文字を JA に入れること"
