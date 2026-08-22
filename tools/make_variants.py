#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""security タスクの摂動変種を生成する (SecLLMHolmes 式 augmentation).

丸暗記とパターン一致を炙り出すため、既存タスクに意味を変えない変換をかけた
変種を作る。元タスクで解けて変種で崩れるなら、それは表層の手がかり
(関数名・変数名・IP など) に反応していた証拠になる。

生成する変種は2種類:

  a (語彙摂動)  … コードなら def 名・定数名・示唆的な引数名を無害な名前へ
                  一斉置換。ログなら IP/ユーザ名/時刻/パスを別の値へ。
                  gold の any_of / location_any_of / allow_extra にも同じ
                  置換を適用するので採点は等価に保たれる。
  b (囮追加)    … コードなら「危険に見えて安全な」ヘルパを追記。ログなら
                  無害だが目を引く行を挿入。gold は変えない。ここを指摘
                  したら純粋な過検出。

使い方:
    python3 tools/make_variants.py            # 生成 (tasks_sec_aug.jsonl も更新)
    python3 tools/make_variants.py --check    # 生成せず整合性チェックのみ
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
BASE_LEDGER = TASKS / "tasks_sec.jsonl"
AUG_LEDGER = TASKS / "tasks_sec_aug.jsonl"

# ── 語彙摂動で使う無害な名前のプール ──────────────────────────────
FUNC_POOL = [
    "fetch_record", "handle_entry", "process_item", "build_payload",
    "resolve_ref", "apply_settings", "collect_stats", "prepare_batch",
    "emit_result", "sync_state", "format_output", "dispatch_task",
    "materialize", "reconcile", "finalize_unit",
]
CONST_POOL = [
    "ROOT_DIR", "DATA_STORE", "PRIMARY_SET", "SERVICE_ROOT", "POLICY_SET",
    "KEY_MATERIAL", "LIMIT_BYTES", "SETTINGS_PATH", "BUCKET_NAME",
]
# 示唆的な引数名 → 中立な名前
# 置換後の名前は短くしない。gold の any_of は部分一致なので、"ref" のような
# 短い語を入れると "reference"/"referrer" に誤マッチする (s05 の "rce" と同じ罠)。
ARG_POOL = ["record_ref", "field_value", "entry_ref", "payload_data",
            "item_ref", "unit_ref", "slot_ref", "chunk_ref"]
SUGGESTIVE = re.compile(
    r"user|raw|input|unsafe|path|_name$|^name$|cmd|command|query|target|"
    r"text|url|cookie|password|token|blob|supplied", re.I
)

# ── 囮 (危険に見えて安全) ────────────────────────────────────────
CODE_DECOY = '''

def _cache_key(payload: bytes) -> str:
    import hashlib

    # キャッシュのキー用。認証にも完全性検証にも使わない。
    return hashlib.sha256(payload).hexdigest()[:16]


def _parse_limit(raw_limit: str) -> int:
    import ast

    # 受け付けるのは Python リテラルのみ。整数でなければ弾く。
    parsed = ast.literal_eval(raw_limit)
    if not isinstance(parsed, int):
        raise ValueError("limit must be an integer")
    return parsed


def _align_columns(rows):
    import subprocess

    proc = subprocess.run(
        ["/usr/bin/column", "-t"],
        input="\\n".join(rows), capture_output=True, text=True, check=True,
    )
    return proc.stdout
'''

CODE_DECOY_EN = CODE_DECOY.replace(
    "# キャッシュのキー用。認証にも完全性検証にも使わない。",
    "# Cache key only; never used for authentication or integrity.",
).replace(
    "# 受け付けるのは Python リテラルのみ。整数でなければ弾く。",
    "# Only Python literals are accepted; non-integers are rejected.",
)

AUTHLOG_DECOY = [
    "Jul 18 03:09:41 web01 sshd[20388]: Accepted publickey for backup from 10.0.5.4 port 49220 ssh2: RSA SHA256:9f2c",
    "Jul 18 03:10:01 web01 CRON[20402]: pam_unix(cron:session): session opened for user root by (uid=0)",
    "Jul 18 03:10:01 web01 CRON[20402]: pam_unix(cron:session): session closed for user root",
    "Jul 18 03:13:12 web01 sudo:   deploy : TTY=pts/0 ; PWD=/srv/app ; USER=root ; COMMAND=/usr/bin/systemctl restart app",
]
ACCESSLOG_DECOY = [
    '10.0.2.15 - - [14/Aug/2026:02:15:00 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"',
    '66.249.66.1 - - [14/Aug/2026:02:15:03 +0000] "GET /sitemap.xml HTTP/1.1" 200 4821 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
    '203.0.113.10 - - [14/Aug/2026:02:15:11 +0000] "GET /static/app.9f2c.css HTTP/1.1" 304 0 "https://shop.example.com/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"',
    '203.0.113.10 - - [14/Aug/2026:02:15:12 +0000] "GET /static/legacy-print.css HTTP/1.1" 404 153 "https://shop.example.com/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"',
]

# ── ログタスクの再匿名化マップ (長い順に置換) ──────────────────────
LOG_RENAMES = {
    "s03": {"203.0.113.66": "198.51.100.212", "Jul 18 03:1": "Sep 02 21:4",
            "web01": "app07", "deploy": "svcops", "oracle": "mysql",
            "postgres": "redis", "admin": "operator"},
    "s11": {"198.51.100.23": "192.0.2.55", "/api/items": "/api/products",
            "14/Aug/2026:02:1": "03/Sep/2026:19:4", "203.0.113.10": "198.51.100.7"},
    "s12": {"203.0.113.10": "192.0.2.31", "198.51.100.77": "10.0.9.14",
            "15/Aug/2026:09:0": "27/Sep/2026:14:3", "66.249.66.1": "66.249.79.8"},
    "s17": {"203.0.113.44": "192.0.2.140", "198.51.100.9": "203.0.113.201",
            "203.0.113.71": "198.51.100.66", "16/Aug/2026:11:0": "01/Oct/2026:08:2",
            "docs.example.com": "handbook.example.net"},
}
LOG_DECOY = {"s03": AUTHLOG_DECOY, "s11": ACCESSLOG_DECOY,
             "s12": ACCESSLOG_DECOY, "s17": ACCESSLOG_DECOY}

FENCE = re.compile(r"```(python|text)\n(.*?)```", re.S)


def _blocks(md: str):
    return list(FENCE.finditer(md))


def _code_of(md: str) -> tuple[str, str]:
    m = _blocks(md)
    if not m:
        raise ValueError("code fence not found")
    return m[0].group(1), m[0].group(2)


def _sub_block(md: str, new_body: str) -> str:
    m = _blocks(md)[0]
    return md[:m.start()] + f"```{m.group(1)}\n{new_body}```" + md[m.end():]


def build_rename_map(code: str) -> dict[str, str]:
    """コードから def 名・定数名・示唆的な引数名の置換表を作る."""
    used = set(re.findall(r"\w+", code))
    fpool = [n for n in FUNC_POOL if n not in used]
    cpool = [n for n in CONST_POOL if n not in used]
    apool = [n for n in ARG_POOL if n not in used]
    mapping: dict[str, str] = {}

    for fn in re.findall(r"^\s*def\s+(\w+)\s*\(", code, re.M):
        if fn.startswith("_") or not fpool:
            continue
        mapping[fn] = fpool.pop(0)

    for const in re.findall(r"^([A-Z][A-Z0-9_]{2,})\s*=", code, re.M):
        if not cpool:
            break
        mapping[const] = cpool.pop(0)

    for sig in re.findall(r"^\s*def\s+\w+\s*\(([^)]*)\)", code, re.M):
        for part in sig.split(","):
            arg = part.split(":")[0].split("=")[0].strip()
            if not arg or not arg.isidentifier() or arg in mapping:
                continue
            if arg in ("self", "cls", "conn", "fn", "args", "kwargs"):
                continue
            if SUGGESTIVE.search(arg) and apool:
                mapping[arg] = apool.pop(0)
    return mapping


def apply_map(text: str, mapping: dict[str, str], word: bool = True) -> str:
    for src in sorted(mapping, key=len, reverse=True):
        pat = rf"\b{re.escape(src)}\b" if word else re.escape(src)
        text = re.sub(pat, mapping[src], text)
    return text


# 短くても誤爆しない既知の略語。これ以外の短い ASCII 語は警告する。
SAFE_SHORT = {
    "md5", "sha1", "ecb", "cbc", "gcm", "sql", "sqli", "xss", "ssti", "ssrf",
    "idor", "csrf", "xxe", "lfi", "rfi", "rsa", "jwt", "hmac", "waf", "dos",
    "toctou", "mfa",
}


def check_short_tokens(gold: dict, where: str) -> list[str]:
    """keywords_all に短い ASCII 語が無いか.

    any_of は「その話題か」の緩いゲートなので短語でも実害は小さいが、
    keywords_all は合否を分ける側なので "rce" が "sourced" に当たるような
    部分一致事故が致命的になる (実際に s05 で起きた)。ここだけ厳しく見る。
    """
    problems = []
    for f in gold.get("findings", []) + gold.get("allow_extra", []):
        for grp in f.get("keywords_all", []):
            for t in (grp if isinstance(grp, (list, tuple)) else [grp]):
                t = str(t)
                if (t.isascii() and t.isalpha() and len(t) <= 4
                        and t.lower() not in SAFE_SHORT):
                    problems.append(
                        f"{where}: keywords_all の {t!r} が短すぎる (部分一致事故の恐れ)")
    return problems


def check_gold_against_issue(gold: dict, issue: str, where: str) -> list[str]:
    """gold の識別子が本文に残っているかを検査する (置換漏れ検出)."""
    problems = []
    low = issue.lower()
    for f in gold.get("findings", []):
        if f.get("any_of") and not any(str(t).lower() in low for t in f["any_of"]):
            problems.append(f"{where}: finding {f.get('id')} の any_of がどれも本文に無い")
        loc = f.get("location_any_of") or []
        if loc and not any(str(t).lower() in low for t in loc):
            problems.append(f"{where}: finding {f.get('id')} の location_any_of がどれも本文に無い")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="生成せず整合性チェックのみ")
    args = ap.parse_args()

    base = [json.loads(l) for l in BASE_LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    out_rows, problems = [], []

    for rec in base:
        tid, bdir = rec["task_id"], rec["dir"]
        src = TASKS / bdir
        en = (src / "issue.md").read_text(encoding="utf-8")
        ja = (src / "issue_ja.md").read_text(encoding="utf-8")
        gold_text = (src / "gold.json").read_text(encoding="utf-8")
        kind, code = _code_of(en)
        is_log = kind == "text"

        # ---- 変種 a: 語彙摂動 -------------------------------------
        if is_log:
            mapping = LOG_RENAMES.get(tid, {})
            en_a = apply_map(en, mapping, word=False)
            ja_a = apply_map(ja, mapping, word=False)
            gold_a = apply_map(gold_text, mapping, word=False)
        else:
            mapping = build_rename_map(code)
            # grader の照合は小文字化して行うため、gold 側には小文字版も当てる
            # (コードの TOKEN_KEY を置換しても gold の "token_key" が残ると
            #  その語が死んで location 判定が緩くなる)。
            gold_map = {**mapping,
                        **{k.lower(): v.lower() for k, v in mapping.items()}}
            en_a = apply_map(en, mapping)
            ja_a = apply_map(ja, mapping)
            gold_a = apply_map(gold_text, gold_map)
        variants = [("a", "ren", "語彙摂動", en_a, ja_a, gold_a)]

        # ---- 変種 b: 囮追加 ---------------------------------------
        if is_log:
            noise = LOG_DECOY.get(tid, ACCESSLOG_DECOY)
            def add_noise(md: str) -> str:
                _, body = _code_of(md)
                lines = body.rstrip("\n").split("\n")
                for i, extra in enumerate(noise):
                    lines.insert(min(len(lines), 2 + i * 3), extra)
                return _sub_block(md, "\n".join(lines) + "\n")
            en_b, ja_b = add_noise(en), add_noise(ja)
        else:
            def add_decoy(md: str, blob: str) -> str:
                _, body = _code_of(md)
                return _sub_block(md, body.rstrip("\n") + "\n" + blob.rstrip("\n") + "\n")
            en_b = add_decoy(en, CODE_DECOY_EN)
            ja_b = add_decoy(ja, CODE_DECOY)
        variants.append(("b", "decoy", "囮追加", en_b, ja_b, gold_text))

        for suffix, slug, label, e, j, g in variants:
            vid = f"{tid}{suffix}"
            vdir = f"{vid}_{bdir.split('_', 1)[1]}_{slug}"
            # 構文チェック (python ブロックのみ)
            if not is_log:
                try:
                    ast.parse(_code_of(e)[1])
                except SyntaxError as exc:
                    problems.append(f"{vid}: 生成コードが構文エラー — {exc}")
            problems += check_short_tokens(json.loads(g), vid)
            problems += check_gold_against_issue(json.loads(g), e, vid)
            problems += check_gold_against_issue(json.loads(g), j, vid + "(ja)")

            if not args.check:
                d = TASKS / vdir
                d.mkdir(parents=True, exist_ok=True)
                (d / "issue.md").write_text(e, encoding="utf-8")
                (d / "issue_ja.md").write_text(j, encoding="utf-8")
                (d / "gold.json").write_text(g, encoding="utf-8")
            out_rows.append({
                "task_id": vid, "dir": vdir, "grader": "detection",
                "domain": "security", "difficulty": rec["difficulty"],
                "title": f"{rec['title']} [{label}]",
            })

    if problems:
        print("⚠️ 整合性の問題:")
        for p in problems:
            print("   ", p)
    if not args.check:
        AUG_LEDGER.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n",
            encoding="utf-8")
        print(f"変種 {len(out_rows)} 件を生成 → {AUG_LEDGER.name}")
    else:
        print(f"チェックのみ: 変種 {len(out_rows)} 件 / 問題 {len(problems)} 件")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
