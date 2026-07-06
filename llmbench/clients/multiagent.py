"""multiagent クライアント — CodeRouter 経由で planner→coder→reviewer を回す.

llmbench/clients/multiagent.py として配置する drop-in クライアント。
LLMClient を実装し、1 回の `generate(system, user)` の内部で役割分離ループを
実行して、最終パッチ (--- FILE: path --- 形式) を返す。llmbench 側の採点・
隠しテスト・pass@k・品質・certify・compare はそのまま再利用される。

設計 (docs/inside/future.md §5):
  - 隠しテストはエージェントに渡らない → 内部ゲートは「構文(ast)」のみ。
    機能テストは llmbench が patch 適用後に隠しテストで判定する。
  - coder には llmbench の SYSTEM_PROMPT (--- FILE: path --- 全置換形式) を
    *そのまま* 渡す → single ベースラインと同一指示で公平。
  - planner: 症状から原因と修正範囲を診断 (複数ファイルでどれを直すか絞る)。
  - reviewer: 過剰修正/回帰を指摘 → REVISE のときだけ coder が 1 回改稿。
  - tokens / latency は全役割の合算 → multi の本当のコストが llmbench の
    tok/s・latency にそのまま乗る (正直な比較)。

config.yaml の models エントリ例:
    multiagent:
      type: multiagent
      base_url: "http://localhost:8088/v1"   # CodeRouter (OpenAI 互換 ingress)
      reviewer: true            # false で planner+coder のみ
      max_iters: 2              # 構文エラー時の coder 再生成上限
      profiles: {planner: planner, coder: coder, reviewer: reviewer}
"""
from __future__ import annotations

import ast
import json
import os
import re
import time
import urllib.error
import urllib.request

from .base import GenerationResult, LLMClient, expand_env

_CODE_BLOCK_RE = re.compile(r"```(?:python|py)?[^\n]*\n(.*?)```", re.DOTALL)

PLANNER_SYS = (
    "You are a senior engineer diagnosing a bug. Given the issue and the source "
    "files, identify the ROOT CAUSE and exactly which file(s) and lines must "
    "change. Output a short, concrete fix plan as an ordered list. Do NOT write "
    "the full corrected file or a patch. Keep it minimal — do not propose "
    "refactors or changes to unrelated code or test files."
)

REVIEWER_SYS = (
    "You are a strict senior code reviewer. You are given a bug issue and a "
    "proposed fix (full corrected files). Check: (a) does it actually fix the "
    "root cause described in the issue? (b) does it modify unrelated code, "
    "over-refactor, or risk a regression? (c) any obvious remaining bug? "
    "Reply with brief findings, then a final line that is EXACTLY one of: "
    "'VERDICT: PASS' (ship as-is) or 'VERDICT: REVISE' (a targeted fix is needed)."
)

_VERDICT_RE = re.compile(r"VERDICT:\s*(PASS|REVISE)", re.IGNORECASE)


class MultiAgentClient(LLMClient):
    """planner→coder→reviewer を CodeRouter 経由で実行する LLMClient."""

    def __init__(self, name: str, cfg: dict):
        super().__init__(name, cfg)
        raw = cfg.get("base_url") or os.environ.get(
            "CODEROUTER_BASE_URL", "http://localhost:8088/v1"
        )
        base = str(expand_env(raw, where=f"models.{name}.base_url")).rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        self.endpoint = base + "/chat/completions"
        self.model = cfg.get("model", "router")  # CodeRouter は profile header で経路決定
        self.use_reviewer = bool(cfg.get("reviewer", True))
        self.max_iters = int(cfg.get("max_iters", 2))
        p = cfg.get("profiles", {}) or {}
        self.profiles = {
            "planner": p.get("planner", "planner"),
            "coder": p.get("coder", "coder"),
            "reviewer": p.get("reviewer", "reviewer"),
        }
        # 役割別トークン内訳 (デバッグ/記事用に raw へ載せる)
        self._roles: list[dict] = []

    # ---- 1 回の wire 呼び出し --------------------------------------------
    def _call(self, role: str, system: str, user: str) -> tuple[str, int, int]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-CodeRouter-Profile": self.profiles[role],
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"[{role}] HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"[{role}] connection failed to {self.endpoint}: {e.reason}. "
                "CodeRouter は起動している?"
            ) from e
        content = body["choices"][0]["message"]["content"] or ""
        usage = body.get("usage") or {}
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
        self._roles.append({"role": role, "profile": self.profiles[role],
                            "prompt_tokens": pt, "completion_tokens": ct})
        return content, pt, ct

    # ---- 構文ゲート (隠しテストが無いので最低限の機械チェック) ----------
    @staticmethod
    def _syntax_error(text: str) -> str | None:
        """出力中の python コードブロックを ast.parse。最初のエラーを返す。"""
        blocks = _CODE_BLOCK_RE.findall(text)
        for code in blocks:
            try:
                ast.parse(code)
            except SyntaxError as e:
                return f"line {e.lineno}: {e.msg}"
        return None

    @staticmethod
    def _has_file_blocks(text: str) -> bool:
        return "FILE:" in text and "```" in text

    # ---- メイン: 役割分離ループ ----------------------------------------
    def _generate(self, system: str, user: str) -> GenerationResult:
        self._roles = []
        t0 = time.monotonic()
        pt_sum = ct_sum = 0

        # 1) planner — 原因診断 + 最小修正方針
        plan, pt, ct = self._call("planner", PLANNER_SYS, user)
        pt_sum += pt; ct_sum += ct

        # 2) coder — llmbench の system (FILE 形式) をそのまま使用。構文NGなら再生成。
        coder_user_base = (
            f"{user}\n\n# Diagnosis and fix plan\n{plan}\n\n"
            "Apply the fix following the plan. Keep changes minimal."
        )
        code_text = ""
        feedback = None
        for _ in range(max(1, self.max_iters)):
            cu = coder_user_base
            if feedback:
                cu += f"\n\n# Your previous output had a syntax error:\n{feedback}\nFix it."
            code_text, pt, ct = self._call("coder", system, cu)
            pt_sum += pt; ct_sum += ct
            err = self._syntax_error(code_text)
            if err is None:
                break
            feedback = err

        # 3) reviewer — 過剰修正/回帰チェック → REVISE のときだけ 1 回改稿
        if self.use_reviewer:
            rev, pt, ct = self._call(
                "reviewer", REVIEWER_SYS,
                f"# Issue\n{user}\n\n# Proposed fix\n{code_text}\n\nReview it.",
            )
            pt_sum += pt; ct_sum += ct
            m = _VERDICT_RE.search(rev)
            verdict = m.group(1).upper() if m else "PASS"
            if verdict == "REVISE":
                revised, pt, ct = self._call(
                    "coder", system,
                    coder_user_base
                    + f"\n\n# Reviewer feedback (apply only what is necessary):\n{rev}",
                )
                pt_sum += pt; ct_sum += ct
                # 改稿はパース可能 & 構文OK のときだけ採用 (改悪を防ぐ)
                if self._has_file_blocks(revised) and self._syntax_error(revised) is None:
                    code_text = revised

        return GenerationResult(
            text=code_text,
            latency_sec=round(time.monotonic() - t0, 2),
            prompt_tokens=pt_sum,
            completion_tokens=ct_sum,
            raw={"roles": list(self._roles)},
        )
