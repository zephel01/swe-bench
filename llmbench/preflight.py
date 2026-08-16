"""llmbench preflight: 走らせる前に「設定が本当に効いているか」を照合する.

探索 (sweep) より先にこれを入れる。2026-08 の Qwen3.8-27B 検証では、
モデルでもハーネスでもなく **設定が意図どおり届いていなかった** ことで
16ラン (約8時間) を捨てた。その事故は次の3つの照合すべてで検出できる。

    A. recommended  — モデル公式の推奨サンプリング vs 実効設定
    B. effective    — config / 実payload / サーバ既定(/props) / 起動引数 の三点照合
    C. degeneration — 既存 artifacts の llm_output.txt を機械的に採点

A と B は生成を1トークンも行わない (ネットワークは /props と HF のみ)。
C は既存の成果物を読むだけ。**GPU時間ゼロで回る。**

使い方::

    llmbench preflight --model local-openai              # A + B
    llmbench preflight --model local-openai --scan results/xxx_artifacts   # + C
    llmbench preflight --scan results/xxx_artifacts      # C だけ
    llmbench preflight --model local-openai --strict     # WARN でも exit 1

exit code: 0 = 問題なし / 1 = FAIL あり (--strict なら WARN も) / 2 = 実行エラー
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- 定数

#: 照合対象のサンプリングキー。clients.SAMPLING_KEYS と揃える。
SAMPLING_KEYS = ("temperature", "top_p", "top_k", "min_p", "seed", "max_tokens")

#: 推奨値からのズレを FAIL 扱いにするキー。
#: temperature だけは「1桁違うと結果が壊れる」ことが実測で分かっているため厳しくする。
STRICT_KEYS = ("temperature",)

#: 浮動小数の同一判定の許容幅。
_EPS = 1e-6

#: 縮退の判定に使う「実質的な行」の最小長。これ未満の行は反復を数えない。
#: ``return None`` や ``try:`` のような短い行は正常なコードでも何十回も出るため
#: (実測: 正常ランで ``self.i += 1`` ×16、``return None`` ×50)、
#: 長さで足切りしないと偽陽性だらけになる。
SUBSTANTIVE_LINE_LEN = 40

#: 縮退指数のしきい値 (warn, fail)。
#: 実測分布から決めている (Qwen3.8-27B / llmbench / 1,860タスク分の llm_output.txt):
#:
#:   指標                  p50    p90     p99      実測max
#:   max_long_line_repeat    1      2       6        1,552
#:   longest_line           69     90   2,339       42,129
#:   max_char_run            0     20      32        7,930
#:
#: 正常帯 (p99) と病的な値のあいだが1〜2桁空いているので、しきい値は
#:   warn = 「そのランに、全体の上位1%に入るタスクが1つでもある」水準 (p99 の 0.9〜3倍)
#:   fail = 「正常帯から1桁外れている」水準 (p99 の 3〜16倍)
#: に置いている。倍率が指標ごとに違うのは、分布の裾の厚みが違うため。
#: **中央値では縮退は見えない。テールでしか見えない**ので、
#: 判定は必ず「ランの最悪タスク」に対して行う (平均を取ってはいけない)。
THRESHOLDS: dict[str, tuple[float, float]] = {
    "max_long_line_repeat": (10, 30),
    "longest_line": (2000, 6000),
    "max_char_run": (100, 500),
    "truncation_rate": (0.05, 0.10),
}

#: 同梱の推奨値テーブル (オフライン時・HF に generation_config.json が無い場合の代替)。
_DATA_DIR = Path(__file__).with_name("data")
_RECOMMENDED_FILE = _DATA_DIR / "recommended_sampling.yaml"

_LEVEL_ORDER = {"OK": 0, "INFO": 1, "WARN": 2, "FAIL": 3}
_LEVEL_MARK = {"OK": "✅", "INFO": "  ", "WARN": "⚠️ ", "FAIL": "❌"}
#: 絵文字を出せないコンソール用 (Windows の cp932/cp437 等)。
#: ここでフォールバックしないと UnicodeEncodeError で preflight ごと落ちる。
_LEVEL_MARK_ASCII = {"OK": "[ OK ]", "INFO": "[ -- ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}


def _marks(stream=None) -> dict:
    """出力先が絵文字を表現できるかを見てマーカーを選ぶ."""
    stream = stream if stream is not None else sys.stdout
    enc = getattr(stream, "encoding", None)
    if not enc:
        return _LEVEL_MARK_ASCII
    try:
        "".join(_LEVEL_MARK.values()).encode(enc)
    except (UnicodeEncodeError, LookupError):
        return _LEVEL_MARK_ASCII
    return _LEVEL_MARK


def _norm_path(value) -> str:
    """パス比較用の正規化.

    Windows は区切りが ``\\`` で大文字小文字を区別しない。macOS も既定では
    区別しない。前方一致でリポジトリを引くだけなので、区切りを ``/`` に
    寄せたうえで、区別しないOSでは小文字化して比較する。
    """
    text = str(value).replace("\\", "/")
    if os.name == "nt" or sys.platform == "darwin":
        text = text.lower()
    return text


def _default_cache_dir() -> Path:
    """OSの作法に沿ったキャッシュ置き場を返す."""
    env = os.environ.get("LLMBENCH_CACHE")
    if env:
        return Path(env)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "llmbench"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "llmbench"
    return Path.home() / ".cache" / "llmbench"


# ---------------------------------------------------------------- データ構造


@dataclass
class Finding:
    """1件の指摘."""

    level: str  # OK / INFO / WARN / FAIL
    check: str  # recommended / effective / degeneration
    key: str
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "check": self.check,
            "key": self.key,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class PreflightReport:
    model: str | None = None
    findings: list[Finding] = field(default_factory=list)
    effective: dict = field(default_factory=dict)
    recommended: dict = field(default_factory=dict)
    recommended_source: str = ""
    server_defaults: dict = field(default_factory=dict)
    launch: dict = field(default_factory=dict)
    degeneration: dict = field(default_factory=dict)
    live_model_path: str | None = None
    repo_id: str | None = None
    base_url: str | None = None

    def add(self, level: str, check: str, key: str, message: str, **detail) -> None:
        self.findings.append(Finding(level, check, key, message, detail))

    @property
    def worst(self) -> str:
        if not self.findings:
            return "OK"
        return max((f.level for f in self.findings), key=lambda x: _LEVEL_ORDER[x])

    def exit_code(self, strict: bool = False) -> int:
        worst = self.worst
        if worst == "FAIL":
            return 1
        if strict and worst == "WARN":
            return 1
        return 0

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "worst": self.worst,
            "findings": [f.to_dict() for f in self.findings],
            "effective": self.effective,
            "recommended": self.recommended,
            "recommended_source": self.recommended_source,
            "base_url": self.base_url,
            "live_model_path": self.live_model_path,
            "repo_id": self.repo_id,
            "server_defaults": self.server_defaults,
            "launch": self.launch,
            "degeneration": self.degeneration,
        }

    def render(self, marks: dict | None = None) -> str:
        mark = marks or _marks()
        lines: list[str] = []
        head = f"preflight: {self.model or '(model指定なし)'}"
        lines.append(head)
        if self.base_url:
            lines.append(f"  接続先: {self.base_url}"
                         + (f"  / ロード中: {self.live_model_path}"
                            if self.live_model_path else "  / サーバ未応答"))
        lines.append("=" * max(len(head), 40))
        by_check: dict[str, list[Finding]] = {}
        for f in self.findings:
            by_check.setdefault(f.check, []).append(f)
        titles = {
            "recommended": "A. 公式推奨との照合",
            "effective": "B. 実効値の三点照合 (config / payload / サーバ)",
            "degeneration": "C. 縮退指数 (既存 artifacts)",
        }
        for check in ("recommended", "effective", "degeneration"):
            items = by_check.get(check)
            if not items:
                continue
            lines.append("")
            lines.append(titles[check])
            lines.append("-" * len(titles[check]))
            for f in sorted(items, key=lambda x: -_LEVEL_ORDER[x.level]):
                lines.append(f"  {mark[f.level]} [{f.key}] {f.message}")
        lines.append("")
        lines.append(f"判定: {self.worst}")
        return "\n".join(lines)


# ---------------------------------------------------------------- 補助


def _num_equal(a, b) -> bool:
    """数値/文字列を型ゆれに強く比較する."""
    if a is None or b is None:
        return a is b
    try:
        return abs(float(a) - float(b)) < _EPS
    except (TypeError, ValueError):
        return str(a) == str(b)


def _fmt(v) -> str:
    if v is None:
        return "未設定"
    if isinstance(v, float) and v == int(v):
        return str(int(v)) if abs(v) >= 1 else str(v)
    return str(v)


def load_recommended_table(path: Path | None = None) -> dict:
    """同梱の推奨値テーブルを読む. 無ければ空 dict."""
    p = Path(path) if path else _RECOMMENDED_FILE
    if not p.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data.get("models", {}) if isinstance(data, dict) else {}


def fetch_generation_config(repo_id: str, *, cache_dir: Path | None = None,
                            offline: bool = False, timeout: float = 10.0) -> dict | None:
    """HuggingFace の generation_config.json を取得する (キャッシュ付き).

    ネットワークを使うのはここだけ。``offline=True`` ならキャッシュのみ。
    取得できなければ None (呼び出し側は同梱テーブルへフォールバックする)。
    """
    cache_dir = Path(cache_dir) if cache_dir else _default_cache_dir()
    cache_dir = cache_dir / "genconfig"
    safe = repo_id.replace("/", "__")
    cached = cache_dir / f"{safe}.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except Exception:
            pass
    if offline:
        return None
    url = f"https://huggingface.co/{repo_id}/raw/main/generation_config.json"
    try:
        import requests

        resp = requests.get(url, timeout=timeout)
        if resp.status_code >= 400:
            return None
        data = resp.json()
    except Exception:
        return None
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return data


def normalize_generation_config(gc: dict) -> dict:
    """generation_config.json をサンプリングキーに正規化する.

    HF は ``do_sample: false`` のとき temperature 等を無視するので、その場合は
    「greedy 推奨」とみなして temperature=0.0 を返す。
    """
    if not isinstance(gc, dict):
        return {}
    if gc.get("do_sample") is False:
        return {"temperature": 0.0}
    out: dict = {}
    for src, dst in (
        ("temperature", "temperature"),
        ("top_p", "top_p"),
        ("top_k", "top_k"),
        ("min_p", "min_p"),
        ("repetition_penalty", "repetition_penalty"),
        ("presence_penalty", "presence_penalty"),
    ):
        if gc.get(src) is not None:
            out[dst] = gc[src]
    return out


def resolve_repo_id(model_name: str, cfg: dict, run_cfg: dict | None = None,
                    live_model_path: str | None = None) -> str | None:
    """モデル設定から HuggingFace repo id を解決する.

    優先順:
      1. ``models.<name>.hf_repo``（明示指定）
      2. ``run.hf_repo_map`` の前方一致。照合するパスは
         **サーバが実際にロードしている GGUF のパス**（``live_model_path``）を
         最優先で使う。``model: "auto"`` 運用では config に model_path が
         書かれないため、config だけ見ても解決できない。
      3. config の ``model_path`` / ``model``

    **パス名からの推測はしない**（誤った推奨値を当てるほうが害が大きい）。
    """
    direct = cfg.get("hf_repo")
    if direct:
        return str(direct)
    mapping = (run_cfg or {}).get("hf_repo_map") or {}
    if not mapping:
        return None
    candidates = [live_model_path,
                  cfg.get("model_path"),
                  cfg.get("model")]
    best: tuple[int, str] | None = None
    for cand in candidates:
        if not cand:
            continue
        cand_n = _norm_path(cand)
        for prefix, repo in mapping.items():
            pre_n = _norm_path(prefix)
            if cand_n.startswith(pre_n):
                if best is None or len(pre_n) > best[0]:
                    best = (len(pre_n), str(repo))
        if best:            # 優先度の高い候補で当たったらそこで確定
            break
    return best[1] if best else None


# ---------------------------------------------------------------- チェックA


def check_recommended(report: PreflightReport, effective: dict, recommended: dict,
                      *, source: str = "", diagnostic: str = "") -> None:
    """公式推奨サンプリングと実効設定を突き合わせる.

    ``diagnostic`` には「何を見て解決に失敗したか」を渡す。
    「設定してください」とだけ言われても、どのパスがどの前方一致に
    当たらなかったのかが分からないと直しようがない。
    """
    report.recommended = dict(recommended)
    report.recommended_source = source
    if not recommended:
        report.add(
            "WARN", "recommended", "-",
            "公式推奨値を取得できませんでした。"
            "models.<name>.hf_repo を設定するか data/recommended_sampling.yaml に追記してください"
            + (f"\n       {diagnostic}" if diagnostic else ""),
        )
        return
    for key, rec in recommended.items():
        if key not in SAMPLING_KEYS:
            continue
        got = effective.get(key)
        if got is None:
            level = "FAIL" if key in STRICT_KEYS else "WARN"
            report.add(
                level, "recommended", key,
                f"公式推奨 {_fmt(rec)} に対して未設定です",
                recommended=rec, effective=None, source=source,
            )
            continue
        if _num_equal(got, rec):
            report.add("OK", "recommended", key,
                       f"公式推奨どおり ({_fmt(rec)})",
                       recommended=rec, effective=got, source=source)
        else:
            level = "FAIL" if key in STRICT_KEYS else "WARN"
            report.add(
                level, "recommended", key,
                f"公式推奨 {_fmt(rec)} に対して {_fmt(got)} を使っています",
                recommended=rec, effective=got, source=source,
            )


# ---------------------------------------------------------------- チェックB


def check_effective(report: PreflightReport, *, cfg_raw: dict, payload: dict,
                    server_defaults: dict | None = None,
                    launch: dict | None = None,
                    class_defaults: dict | None = None,
                    n_ctx: int | None = None) -> None:
    """config / 実payload / サーバ既定 / 起動引数 の三点照合.

    ここが本命。2026-08 の事故は次の2つで、どちらもこの関数が検出する。

      1. ``seed`` / ``top_p`` / ``top_k`` / ``min_p`` が payload に載っておらず、
         llama-server 既定 (seed=-1 = 毎回ランダム) が効いていた
      2. ``temperature`` を config に書いていなかったため、
         llmbench のクラス既定 0.2 が黙って使われていた
    """
    server_defaults = server_defaults or {}
    launch = launch or {}
    class_defaults = class_defaults or {}
    report.server_defaults = dict(server_defaults)
    report.launch = {k: v for k, v in launch.items() if k in
                     ("temp", "top_p", "top_k", "min_p", "seed", "n_ctx", "spec_type")}

    for key in SAMPLING_KEYS:
        in_payload = key in payload and payload[key] is not None
        in_cfg = cfg_raw.get(key) is not None
        srv = server_defaults.get(key)

        if not in_payload:
            if srv is not None:
                report.add(
                    "WARN", "effective", key,
                    f"payload に載っていません。サーバ既定 {_fmt(srv)} が効きます"
                    f"{'（configには書いてあります）' if in_cfg else ''}",
                    in_payload=False, config=cfg_raw.get(key), server_default=srv,
                )
            else:
                report.add(
                    "INFO", "effective", key,
                    "payload に載っていません（サーバ既定に従います）",
                    in_payload=False, config=cfg_raw.get(key),
                )
            continue

        value = payload[key]
        if not in_cfg and key in class_defaults:
            report.add(
                "WARN", "effective", key,
                f"config に指定がないため llmbench 既定 {_fmt(class_defaults[key])} が"
                f"使われています。**モデルの推奨値ではありません**",
                in_payload=True, effective=value, class_default=class_defaults[key],
            )
        else:
            report.add("OK", "effective", key, f"payload に {_fmt(value)} を送信します",
                       in_payload=True, effective=value)

        # 起動引数との不一致 (payload が優先されるので情報提供のみ)
        launch_key = "temp" if key == "temperature" else key
        lv = launch.get(launch_key)
        if lv is not None and not _num_equal(lv, value):
            report.add(
                "INFO", "effective", key,
                f"起動引数は {_fmt(lv)} ですが payload の {_fmt(value)} が優先されます",
                launch=lv, effective=value,
            )

    # seed 未指定 = 再現性なし
    if payload.get("seed") is None:
        report.add(
            "WARN", "effective", "seed",
            "seed 未指定です。llama-server の既定は seed=-1（毎回ランダム）なので、"
            "このランは後から再現・検証できません"
            "（seed を指定すれば、同じタスク集合を同じ順序で回す限りは"
            "実測でビット単位まで再現します。ただしタスク集合を変えると"
            "KVキャッシュの残り方が変わるので再現しません）",
            seed_sent=False,
        )

    # max_tokens が n_ctx を食い切っていないか
    mt = payload.get("max_tokens")
    ctx = n_ctx or launch.get("n_ctx")
    if mt and ctx:
        try:
            mt_i, ctx_i = int(mt), int(ctx)
        except (TypeError, ValueError):
            mt_i = ctx_i = 0
        if mt_i and ctx_i and mt_i >= ctx_i:
            report.add(
                "FAIL", "effective", "max_tokens",
                f"max_tokens {mt_i:,} が n_ctx {ctx_i:,} 以上です。"
                f"実効上限は n_ctx − プロンプト長になり、max_tokens は効きません",
                max_tokens=mt_i, n_ctx=ctx_i,
            )
        elif mt_i and ctx_i and mt_i > ctx_i * 0.9:
            report.add(
                "WARN", "effective", "max_tokens",
                f"max_tokens {mt_i:,} が n_ctx {ctx_i:,} の90%を超えています。"
                f"長いプロンプトのタスクでは max_tokens に届く前に ctx が尽きます",
                max_tokens=mt_i, n_ctx=ctx_i,
            )


# ---------------------------------------------------------------- チェックC


_CHAR_RUN_RE = re.compile(r"(.)\1{19,}", re.DOTALL)


def degeneration_metrics(text: str) -> dict:
    """1本の生成テキストから縮退の指標を出す (テスト実行不要).

    - ``max_long_line_repeat``: **40文字以上**の同一行が何回出たか（判定に使う）
    - ``max_line_repeat``: 長さを問わない同一行の反復（参考値。正常でも大きくなる）
    - ``longest_line``: 最長1行の文字数
    - ``max_char_run``: 同一文字が連続した最長ラン
    """
    if not text:
        return {"max_long_line_repeat": 0, "max_line_repeat": 0, "repeated_line": "",
                "longest_line": 0, "max_char_run": 0, "chars": 0, "lines": 0}
    raw_lines = text.splitlines()
    stripped = [ln.strip() for ln in raw_lines]
    non_empty = [ln for ln in stripped if ln]
    all_count = Counter(non_empty).most_common(1)[0][1] if non_empty else 0
    substantive = [ln for ln in non_empty if len(ln) >= SUBSTANTIVE_LINE_LEN]
    if substantive:
        line, count = Counter(substantive).most_common(1)[0]
    else:
        line, count = "", 0
    longest = max((len(ln) for ln in raw_lines), default=0)
    run = 0
    for m in _CHAR_RUN_RE.finditer(text):
        run = max(run, len(m.group(0)))
    return {
        "max_long_line_repeat": count,
        "max_line_repeat": all_count,
        "repeated_line": line[:120],
        "longest_line": longest,
        "max_char_run": run,
        "chars": len(text),
        "lines": len(raw_lines),
    }


def _level_for(name: str, value: float) -> str:
    warn, fail = THRESHOLDS[name]
    if value >= fail:
        return "FAIL"
    if value >= warn:
        return "WARN"
    return "OK"


def scan_artifacts(artifacts_dir: Path, *, results_json: Path | None = None) -> dict:
    """artifacts ディレクトリ配下の llm_output.txt を全部採点する.

    戻り値は ``{"tasks": {task_id: metrics}, "worst": {...}, "truncation": {...}}``。
    ``results_json`` を渡すと打ち切り率も集計する。
    """
    artifacts_dir = Path(artifacts_dir)
    tasks: dict[str, dict] = {}
    for out in sorted(artifacts_dir.glob("*/llm_output.txt")):
        try:
            text = out.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tasks[out.parent.name] = degeneration_metrics(text)

    worst: dict[str, dict] = {}
    for name in ("max_long_line_repeat", "longest_line", "max_char_run"):
        best_id, best_val = "", 0
        for tid, m in tasks.items():
            if m[name] > best_val:
                best_id, best_val = tid, m[name]
        worst[name] = {"task": best_id, "value": best_val,
                       "level": _level_for(name, best_val)}

    trunc: dict = {}
    if results_json and Path(results_json).exists():
        try:
            data = json.loads(Path(results_json).read_text(encoding="utf-8"))
            rows = data.get("results", [])
            n = len(rows)
            hit = [r.get("task_id") for r in rows if r.get("truncated")]
            if not hit:  # 旧ハーネス互換: truncated が無い場合は completion_tokens で推定
                hit = [
                    r.get("task_id") for r in rows
                    if r.get("max_tokens") and r.get("completion_tokens")
                    and r["completion_tokens"] >= int(r["max_tokens"]) * 0.98
                ]
            rate = (len(hit) / n) if n else 0.0
            trunc = {"n_tasks": n, "n_truncated": len(hit), "rate": rate,
                     "tasks": hit, "level": _level_for("truncation_rate", rate)}
        except Exception:
            trunc = {}
    return {"tasks": tasks, "worst": worst, "truncation": trunc}


def check_degeneration(report: PreflightReport, scan: dict) -> None:
    report.degeneration = scan
    labels = {
        "max_long_line_repeat": "同一行(40字以上)の最大反復",
        "longest_line": "最長1行の文字数",
        "max_char_run": "同一文字の最長連続",
    }
    for name, label in labels.items():
        w = scan.get("worst", {}).get(name)
        if not w:
            continue
        warn, fail = THRESHOLDS[name]
        task = w.get("task") or "-"
        value = w.get("value", 0)
        msg = f"{label} = {value:,}（{task}）"
        if w.get("level") == "OK":
            report.add("OK", "degeneration", name, msg + f" / 警告閾値 {warn:,}",
                       task=task, value=value, warn=warn, fail=fail)
            continue
        detail = ""
        if name == "max_long_line_repeat" and w.get("task"):
            line = scan["tasks"].get(w["task"], {}).get("repeated_line", "")
            if line:
                detail = f" 反復行: {line!r}"
        report.add(
            w["level"], "degeneration", name,
            msg + f" — 縮退ループの疑い（閾値 warn {warn:,} / fail {fail:,}）" + detail,
            task=task, value=value, warn=warn, fail=fail,
        )
    tr = scan.get("truncation") or {}
    if tr:
        rate = tr["rate"]
        msg = f"打ち切り {tr['n_truncated']}/{tr['n_tasks']} = {rate * 100:.1f}%"
        detail = {k: v for k, v in tr.items() if k != "level"}
        if tr["level"] == "OK":
            report.add("OK", "degeneration", "truncation_rate", msg, **detail)
        else:
            report.add(tr["level"], "degeneration", "truncation_rate",
                       msg + " — 思考が収束していない可能性。"
                             "予算を増やす前にサンプリングを疑うこと", **detail)


# ---------------------------------------------------------------- 統合


def run_preflight(config: dict, model_name: str | None, *,
                  artifacts: str | Path | None = None,
                  results_json: str | Path | None = None,
                  offline: bool = False,
                  recommended_table: Path | None = None) -> PreflightReport:
    """A/B/C をまとめて実行する.

    ``model_name`` を省略すると C (縮退スキャン) だけを行う。
    """
    report = PreflightReport(model=model_name)

    if model_name:
        from .clients import SAMPLING_KEYS as CLIENT_KEYS  # noqa: F401
        from .clients import create_client, sampling_of

        models = (config or {}).get("models", {})
        cfg_raw = dict(models.get(model_name) or {})
        if not cfg_raw:
            report.add("FAIL", "effective", "-",
                       f"config に models.{model_name} がありません")
            return report
        run_cfg = (config or {}).get("run", {}) or {}
        try:
            client = create_client(model_name, cfg_raw, run_cfg.get("sampling"))
        except Exception as e:
            # model: "auto" はサーバの /v1/models を引くので、推論サーバが
            # 動いていないマシン (開発機など) では必ずここで失敗する。
            # 例外で落とさずレポートにする。C (縮退指数) は続行できる。
            report.add(
                "WARN", "effective", "-",
                f"クライアントを生成できませんでした: {e}\n"
                f"       model: {cfg_raw.get('model')!r} / base_url: "
                f"{cfg_raw.get('base_url')!r}\n"
                "       **A と B は推論サーバが動いているマシンで実行してください。**"
                "開発機で確認したいだけなら model に固定名を書けば B の payload 検査までは通ります",
                base_url=cfg_raw.get("base_url"), model=cfg_raw.get("model"),
            )
            client = None
        if client is not None:
            effective = sampling_of(client)
            report.effective = dict(effective)

            # --- 実 payload をそのまま覗く (推測しない)
            payload: dict = {}
            if hasattr(client, "_build_payload"):
                try:
                    payload = client._build_payload("", "")
                except Exception as e:  # pragma: no cover - 実サーバ依存
                    report.add("WARN", "effective", "-",
                               f"payload を構築できませんでした: {e}")
            else:
                payload = {k: v for k, v in effective.items() if k in SAMPLING_KEYS}

            # --- サーバ既定 / 起動引数
            server_defaults, launch, n_ctx = {}, {}, None
            live_model_path: str | None = None
            base_url = getattr(client, "base_url", "")
            report.base_url = base_url or None
            if base_url:
                try:
                    from . import env as env_mod

                    props = env_mod._get_json(f"{base_url.rsplit('/v1', 1)[0]}/props")
                    server_defaults = env_mod.sampler_defaults(props)
                    if isinstance(props, dict):
                        gen = props.get("default_generation_settings") or {}
                        n_ctx = gen.get("n_ctx") or props.get("n_ctx")
                        # ロード中モデルの実パス。model: "auto" 運用ではこれが唯一の手がかり
                        live_model_path = (props.get("model_path")
                                           or gen.get("model") or None)
                    pid = env_mod.find_server_pid(env_mod._port_of(base_url))
                    if pid:
                        launch = env_mod.parse_server_args(env_mod._proc_argv(pid))
                except Exception:
                    pass

            if server_defaults and not launch:
                report.add(
                    "INFO", "effective", "-",
                    "サーバ既定(/props)は取得できましたが、起動引数(argv)は読めませんでした。"
                    "**llama-server が別マシンで動いている**か、このOSではプロセス引数を"
                    "取得できません。起動引数との突き合わせだけがスキップされます",
                )
            if not server_defaults and not launch:
                report.add(
                    "INFO", "effective", "-",
                    f"{base_url} に接続できず、サーバ既定(/props)と起動引数を"
                    "照合できませんでした。**llama-server を起動した状態で実行すると"
                    "検査が増えます**（n_ctx との突き合わせなど）",
                )
            class_defaults = {"temperature": 0.2, "max_tokens": 4096}
            check_effective(report, cfg_raw=cfg_raw, payload=payload,
                            server_defaults=server_defaults, launch=launch,
                            class_defaults=class_defaults, n_ctx=n_ctx)

            # --- 公式推奨
            recommended, source = {}, ""
            repo_id = resolve_repo_id(model_name, cfg_raw, run_cfg,
                                      live_model_path=live_model_path)
            report.live_model_path = live_model_path
            report.repo_id = repo_id
            if repo_id:
                gc = fetch_generation_config(repo_id, offline=offline)
                if gc:
                    recommended = normalize_generation_config(gc)
                    source = f"huggingface.co/{repo_id}/generation_config.json"
            if not recommended:
                table = load_recommended_table(recommended_table)
                key = repo_id or cfg_raw.get("recommended_key") or model_name
                entry = table.get(key) or {}
                mode = cfg_raw.get("thinking_mode") or entry.get("default_mode") or "thinking"
                vals = (entry.get("modes") or {}).get(mode) or {}
                if vals:
                    recommended = dict(vals)
                    source = f"{_RECOMMENDED_FILE.name}: {key} / {mode}"

            # 解決に失敗したときは「何を見たか」を必ず出す
            diag = ""
            if not recommended:
                seen = live_model_path or cfg_raw.get("model_path") or cfg_raw.get("model")
                prefixes = list((run_cfg.get("hf_repo_map") or {}).keys())
                parts = [f"照合に使ったパス: {seen!r}"]
                if live_model_path is None:
                    parts.append("(サーバから取得できず。llama-server を起動して実行するか "
                                 "models.<name>.hf_repo を明示してください)")
                if prefixes:
                    parts.append(f"run.hf_repo_map の前方一致候補: {prefixes}")
                else:
                    parts.append("run.hf_repo_map が未設定です")
                if repo_id:
                    parts.append(f"→ repo_id={repo_id} は解決できたが推奨値が引けませんでした "
                                 "(オフライン or テーブル未登録)")
                diag = " / ".join(parts)

            check_recommended(report, effective, recommended, source=source,
                              diagnostic=diag)

    if artifacts:
        scan = scan_artifacts(Path(artifacts), results_json=(
            Path(results_json) if results_json else _guess_results(Path(artifacts))))
        check_degeneration(report, scan)

    return report


def _guess_results(artifacts_dir: Path) -> Path | None:
    """``..._artifacts`` の隣にある ``..._results.json`` を推測する."""
    name = artifacts_dir.name
    if name.endswith("_artifacts"):
        cand = artifacts_dir.with_name(name[: -len("_artifacts")] + "_results.json")
        if cand.exists():
            return cand
    return None
