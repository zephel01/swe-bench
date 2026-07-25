"""サブスクCLIクライアント — 定額プラン枠でエージェントCLIをヘッドレス実行する.

Claude Pro/Max・ChatGPT (Codex)・SuperGrok などのチャットサブスクリプションは
OpenAI互換APIを公式には提供しないが、各社の公式CLIはサブスク認証のまま
非対話 (ヘッドレス) 実行できる:

  - Claude Code : ``claude -p "<prompt>" --output-format json``
  - Codex CLI   : ``codex exec "<prompt>" --output-last-message <file>``
  - Grok Build  : ``grok exec "<prompt>"``

このクライアントはそれらを subprocess で呼び、最終出力を GenerationResult に
正規化する。プリセット (claude / codex / grok) か、任意の command 指定
(preset: custom) で他のCLIにも接続できる。

⚠️ ベンチマークとしての注意 (README / USAGE 参照):
  - 測っているのは「素のモデル」ではなく **エージェント製品 (CLI+モデル)**。
    システムプロンプト・自律リトライが乗るため、素の補完 (type: openai) と
    同列比較しないこと。
  - temperature は制御できない。``--runs N`` の sample_temp は無視される
    (初回生成時に警告を出す)。
  - サブスクのレート枠 (5時間ウィンドウ / 週次上限) に達するとCLIがエラーを
    返し、そのタスクは失点扱いになる。分割実行 + ``certify --merge`` を推奨。
  - 各生成は空の一時ディレクトリを cwd にして実行する (エージェントが
    手元のリポジトリを読み書きしないように)。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import GenerationResult, LLMClient, expand_env

# プリセット定義:
#   argv       : 基本コマンド
#   prompt_via : stdin | arg  (プロンプトの渡し方)
#   model_flag : cfg["model"] 指定時に付けるフラグ
#   parse      : claude_json | last_message_file | stdout
PRESETS: dict[str, dict] = {
    "claude": {
        "argv": ["claude", "-p", "--output-format", "json"],
        "prompt_via": "stdin",
        "model_flag": "--model",
        "parse": "claude_json",
        "install_hint": (
            "Claude Code CLI が必要です: npm install -g @anthropic-ai/claude-code"
            " → `claude` を一度起動して Pro/Max アカウントでログイン"
        ),
    },
    "codex": {
        "argv": ["codex", "exec", "--skip-git-repo-check"],
        "prompt_via": "arg",
        "model_flag": "--model",
        "parse": "last_message_file",
        "install_hint": (
            "Codex CLI が必要です: npm install -g @openai/codex"
            " → `codex` を一度起動して ChatGPT アカウントでログイン"
        ),
    },
    "grok": {
        "argv": ["grok", "exec"],
        "prompt_via": "arg",
        "model_flag": "--model",
        "parse": "stdout",
        "install_hint": (
            "Grok Build CLI が必要です (xAI公式のインストーラで導入し、"
            "X / xAI アカウントでログイン)"
        ),
    },
    # custom: cfg["command"] 必須。parse は cfg["parse"] (既定 stdout)
    "custom": {
        "argv": [],
        "prompt_via": "arg",
        "model_flag": None,
        "parse": "stdout",
        "install_hint": "",
    },
}

_LAST_MSG_FLAG = "--output-last-message"

# codex exec 等がバナーに出す「model: <名前>」行 (stdout冒頭/stderrから検出)
_MODEL_LINE_RE = re.compile(r"(?im)^\s*model:\s*([\w.\-/:]+)\s*$")


def _model_from_claude_json(data: dict) -> str | None:
    """claude -p の JSON 応答から実行モデル名を取り出す.

    新しめのCLIは modelUsage (モデル名 → トークン集計) を含む。複数モデル
    (メイン + サブエージェントの haiku 等) の場合は出力トークン最大を採用。
    """
    mu = data.get("modelUsage")
    if isinstance(mu, dict) and mu:
        def _out(v) -> int:
            return int(v.get("outputTokens", 0)) if isinstance(v, dict) else 0
        return max(mu, key=lambda k: _out(mu[k]))
    m = data.get("model")
    return str(m) if m else None


class CliAgentClient(LLMClient):
    """公式エージェントCLIをサブプロセス実行するクライアント (type: cli)."""

    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        preset_name = str(cfg.get("preset", "custom")).lower()
        if preset_name not in PRESETS:
            raise ValueError(
                f"models.{name}: 未知の preset {preset_name!r}。"
                f"有効値: {', '.join(PRESETS)}"
            )
        preset = PRESETS[preset_name]
        self.preset = preset_name

        # command: プリセットargvの差し替え (custom では必須)
        command = cfg.get("command") or preset["argv"]
        if isinstance(command, str):
            command = command.split()
        if not command:
            raise ValueError(
                f"models.{name}: preset: custom では command が必須です "
                "(例 command: ['mycli', 'run', '--json'])"
            )
        self.command = [expand_env(c, where=f"models.{name}.command") for c in command]

        self.prompt_via = cfg.get("prompt_via", preset["prompt_via"])
        if self.prompt_via not in ("stdin", "arg"):
            raise ValueError(
                f"models.{name}: prompt_via は stdin | arg のいずれかです"
            )
        self.parse_mode = cfg.get("parse", preset["parse"])
        self.model_flag = cfg.get("model_flag", preset["model_flag"])
        self.model = str(
            expand_env(cfg.get("model", ""), where=f"models.{name}.model") or ""
        ).strip()
        self.extra_args = [
            str(expand_env(a, where=f"models.{name}.extra_args"))
            for a in (cfg.get("extra_args") or [])
        ]
        # 追加環境変数 (トークン等は ${VAR} で参照)
        self.env = {
            str(k): str(expand_env(v, where=f"models.{name}.env"))
            for k, v in (cfg.get("env") or {}).items()
        }
        self.install_hint = preset["install_hint"]
        self._cfg_temperature = self.temperature
        self._warned_temperature = False
        # CLI応答から検出した実行モデル名 (runner が結果に記録する)
        self.detected_model: str | None = None

    def _note_model(self, model: str | None) -> None:
        """CLI応答から検出した実行モデルを記録し、初回/変更時に表示する."""
        model = (model or "").strip()
        if not model or model == self.detected_model:
            return
        changed = self.detected_model is not None
        self.detected_model = model
        mark = "⚠️ 実行モデルが変わりました" if changed else "🔎 実行モデル"
        print(f"{mark}: {model} ({self.name}: CLI応答から検出)", file=sys.stderr)

    # ---- コマンド組み立て ----

    def build_argv(self, prompt: str, last_msg_path: Path | None) -> list[str]:
        argv = list(self.command)
        if self.model and self.model_flag:
            argv += [self.model_flag, self.model]
        argv += self.extra_args
        if self.parse_mode == "last_message_file" and last_msg_path is not None:
            argv += [_LAST_MSG_FLAG, str(last_msg_path)]
        if self.prompt_via == "arg":
            argv.append(prompt)
        return argv

    # ---- 出力パース ----

    def _parse_output(self, stdout: str, last_msg_path: Path | None) -> GenerationResult:
        if self.parse_mode == "claude_json":
            try:
                data = json.loads(stdout)
            except (json.JSONDecodeError, ValueError):
                # --output-format json が効いていない等 → 生stdoutで続行
                return GenerationResult(text=stdout.strip(), raw={"stdout": stdout})
            usage = data.get("usage") or {}
            if data.get("is_error"):
                raise RuntimeError(
                    f"{self.command[0]} がエラーを返しました: "
                    f"{str(data.get('result', ''))[:300]}"
                )
            self._note_model(_model_from_claude_json(data))
            return GenerationResult(
                text=str(data.get("result", "")),
                prompt_tokens=usage.get("input_tokens"),
                completion_tokens=usage.get("output_tokens"),
                raw=data,
            )
        if self.parse_mode == "last_message_file":
            if last_msg_path is not None and last_msg_path.exists():
                text = last_msg_path.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    return GenerationResult(text=text, raw={"stdout": stdout})
            # ファイル未出力 (旧版CLI等) → stdout にフォールバック
            return GenerationResult(text=stdout.strip(), raw={"stdout": stdout})
        # stdout
        return GenerationResult(text=stdout.strip(), raw={"stdout": stdout})

    # ---- 生成 ----

    def _generate(self, system: str, user: str) -> GenerationResult:
        if (
            self.temperature != self._cfg_temperature
            and not self._warned_temperature
        ):
            self._warned_temperature = True
            print(
                f"⚠️ {self.name} (type: cli) は temperature を制御できません。"
                f"sample_temp={self.temperature} は無視されます "
                "(試行間の多様性はCLI側の既定サンプリングに依存)",
                file=sys.stderr,
            )
        # エージェントCLIは自前のシステムプロンプトを持つため、
        # llmbench の system は user プロンプトに前置して渡す。
        prompt = f"{system.strip()}\n\n{user}" if system.strip() else user

        exe = self.command[0]
        if shutil.which(exe) is None:
            hint = f"\n  {self.install_hint}" if self.install_hint else ""
            raise ValueError(
                f"models.{self.name}: コマンド {exe!r} が見つかりません。{hint}"
            )

        # 空の一時cwdで実行 (エージェントに手元のファイルを触らせない)
        with tempfile.TemporaryDirectory(prefix="llmbench_cli_") as tmp:
            tmp_path = Path(tmp)
            last_msg_path = (
                tmp_path / "last_message.txt"
                if self.parse_mode == "last_message_file" else None
            )
            argv = self.build_argv(prompt, last_msg_path)
            env = {**os.environ, **self.env}
            try:
                proc = subprocess.run(
                    argv,
                    input=prompt if self.prompt_via == "stdin" else None,
                    capture_output=True,
                    text=True,
                    cwd=tmp,
                    env=env,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"{exe} が {self.timeout}s でタイムアウトしました "
                    f"(models.{self.name}.timeout で延長可能)"
                ) from e
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
                raise RuntimeError(
                    f"{exe} exit={proc.returncode}: {err[:500]}"
                    " (サブスクのレート枠超過・未ログインの可能性。"
                    f"`{exe}` を単体実行して確認してください)"
                )
            if self.parse_mode != "claude_json":
                # codex/grok系: バナーの「model: <名前>」行から実行モデルを検出
                # (誤検出を避けるため stdout は冒頭のみ走査)
                head = "\n".join((proc.stdout or "").splitlines()[:15])
                m = _MODEL_LINE_RE.search((proc.stderr or "") + "\n" + head)
                if m:
                    self._note_model(m.group(1))
            return self._parse_output(proc.stdout or "", last_msg_path)
