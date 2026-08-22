"""detection gold の当たり判定テスト (ネットワーク不要).

`llmbench validate` は mock_gold が gold から機械生成されるため
「gold が現実のモデル回答で当たるか」は検証できない。ここでは英語/日本語の
現実的な回答文を gold に当て、
  1. 正しい回答が resolved 相当 (F1 >= pass_f1) になること
  2. 誤検出 (別クラスの指摘) が gold をカバーしないこと
を確認する。
"""

from __future__ import annotations

import json
import pathlib

from llmbench.graders.detection import _covers, _serialize

TASKS = pathlib.Path(__file__).resolve().parent.parent / "tasks"
PASS_F1 = 0.67


def _doc(task_dir: str) -> dict:
    return json.loads((TASKS / task_dir / "gold.json").read_text(encoding="utf-8"))


def _gold(task_dir: str) -> list[dict]:
    return _doc(task_dir)["findings"]


def _classify(task_dir: str, preds: list[dict]) -> tuple[int, int, int]:
    """予測を (TP, 中立, FP) に振り分ける (detection grader と同じ規則)."""
    doc = _doc(task_dir)
    gold, allow = doc["findings"], doc.get("allow_extra", [])
    tp = neutral = fp = 0
    for pred in preds:
        pt = _serialize(pred)
        if any(_covers(pt, g) for g in gold):
            tp += 1
        elif allow and any(_covers(pt, a) for a in allow):
            neutral += 1
        else:
            fp += 1
    return tp, neutral, fp


def _f1(task_dir: str, preds: list[dict]) -> float:
    gold = _gold(task_dir)
    tp, _neutral, fp = _classify(task_dir, preds)
    n_scored = tp + fp
    if not gold:
        return 1.0 if n_scored == 0 else 0.0
    pts = [_serialize(p) for p in preds]
    covered = [g for g in gold if any(_covers(pt, g) for pt in pts)]
    recall = len(covered) / len(gold)
    precision = (tp / n_scored) if n_scored else 0.0
    return (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0


# ── 1. 現実的な正解回答が通ること (英語) ────────────────────────────
GOOD_EN = {
    "s01_pathtrav": [{"type": "Path Traversal (CWE-22)", "location": "load_document",
                      "evidence": "os.path.join(BASE_DIR, user_path) with ../"}],
    "s02_sqli": [{"type": "SQL Injection (CWE-89)", "location": "cursor.execute",
                  "evidence": "username concatenated into the query"}],
    "s03_bruteforce": [{"type": "SSH brute force (CWE-307)", "location": "203.0.113.66",
                        "evidence": "15 Failed password then Accepted password for deploy"}],
    "s05_cmdinj": [{"type": "OS Command Injection (CWE-78)", "location": "create_archive",
                    "evidence": "subprocess.run(cmd, shell=True) with project name"}],
    "s06_deserial": [{"type": "Insecure Deserialization (CWE-502)", "location": "decode_session",
                      "evidence": "pickle.loads on the session_state cookie"}],
    "s07_ssrf": [{"type": "SSRF (CWE-918)", "location": "fetch_preview",
                  "evidence": "requests.get(target_url); blocklist misses 169.254.169.254"}],
    "s08_idor": [{"type": "IDOR / Broken Access Control", "location": "invoice_detail",
                  "evidence": "owner_id never compared to the session user"}],
    "s09_crypto": [
        {"type": "Weak password hash (CWE-916)", "location": "hash_password", "evidence": "hashlib.md5 without salt"},
        {"type": "AES-ECB (CWE-327)", "location": "encrypt_token", "evidence": "modes.ECB()"},
        {"type": "Hardcoded key (CWE-798)", "location": "TOKEN_KEY", "evidence": "hardcoded 0123456789abcdef"},
    ],
    "s11_weblog": [{"type": "SQL Injection (CWE-89)", "location": "198.51.100.23 -> /api/items",
                    "evidence": "UNION SELECT username,password_hash FROM users returned 264913 bytes"}],
    "s13_toctou": [
        {"type": "TOCTOU race (CWE-367)", "location": "publish_report", "evidence": "os.stat check then open(target)"},
        {"type": "Insecure temp file (CWE-377)", "location": "stage_upload", "evidence": "tempfile.mktemp"},
    ],
    "s14_ssti_xss": [
        {"type": "SSTI (CWE-1336)", "location": "greet", "evidence": "render_template_string with user input"},
        {"type": "Reflected XSS (CWE-79)", "location": "note", "evidence": "Markup(text) disables escaping"},
        {"type": "Debug mode enabled", "location": "app.run", "evidence": "debug=True on 0.0.0.0"},
        {"type": "Hardcoded secret", "location": "app.secret_key", "evidence": "secret_key = dev-secret-key"},
    ],
}

# ── 2. 同じ内容の日本語回答も通ること (language tax が採点側で発生しない) ──
GOOD_JA = {
    "s01_pathtrav": [{"type": "パストラバーサル", "location": "load_document",
                      "evidence": "os.path.join に user_path をそのまま結合している"}],
    "s02_sqli": [{"type": "SQLインジェクション", "location": "cursor.execute",
                  "evidence": "username を文字列連結して query を組み立てている"}],
    "s03_bruteforce": [{"type": "SSHブルートフォース攻撃", "location": "203.0.113.66",
                        "evidence": "Failed password が多数続いた後に Accepted password"}],
    "s05_cmdinj": [{"type": "OSコマンドインジェクション", "location": "create_archive",
                    "evidence": "shell=True で project を連結して実行している"}],
    "s06_deserial": [{"type": "安全でないデシリアライズ", "location": "decode_session",
                      "evidence": "Cookie の値を pickle.loads で復元している"}],
    "s07_ssrf": [{"type": "SSRF (サーバサイドリクエストフォージェリ)", "location": "fetch_preview",
                  "evidence": "BLOCKED_HOSTS が不十分なまま requests.get を実行"}],
    "s08_idor": [{"type": "認可不備 (IDOR)", "location": "invoice_detail",
                  "evidence": "owner_id とセッションの user_id を突き合わせていない"}],
    "s09_crypto": [
        {"type": "脆弱なパスワードハッシュ", "location": "hash_password", "evidence": "ソルト無しの md5"},
        {"type": "不適切な暗号利用モード", "location": "encrypt_token", "evidence": "AES の ECB モード"},
        {"type": "鍵のハードコード", "location": "TOKEN_KEY", "evidence": "ソースに鍵がハードコードされている"},
    ],
    "s11_weblog": [{"type": "SQLインジェクションによる情報窃取", "location": "198.51.100.23 の /api/items",
                    "evidence": "UNION SELECT で information_schema と users を列挙している"}],
    "s13_toctou": [
        {"type": "TOCTOU 競合状態", "location": "publish_report",
         "evidence": "os.stat の確認後に open(target) しておりシンボリックリンクで差し替え可能"},
        {"type": "安全でない一時ファイル", "location": "stage_upload", "evidence": "tempfile.mktemp を使用"},
    ],
    "s14_ssti_xss": [
        {"type": "サーバサイドテンプレートインジェクション (SSTI)", "location": "greet",
         "evidence": "render_template_string にユーザー入力を連結"},
        {"type": "反射型XSS", "location": "note", "evidence": "Markup(text) でエスケープが無効化されている"},
        {"type": "デバッグモード有効", "location": "app.run", "evidence": "debug=True のまま 0.0.0.0 で公開"},
        {"type": "シークレットのハードコード", "location": "app.secret_key", "evidence": "secret_key がソース直書き"},
    ],
}

# ── 3. 別クラスの誤検出が gold をカバーしないこと (甘すぎない) ──────────
BAD = [
    ("s05_cmdinj", {"type": "Path traversal", "location": "create_archive",
                    "evidence": "project name used in a path"}),
    ("s06_deserial", {"type": "Unsafe YAML load", "location": "load_profile_defaults",
                      "evidence": "yaml.safe_load"}),
    ("s08_idor", {"type": "SQL Injection", "location": "get_invoice",
                  "evidence": "cursor.execute with invoice_id"}),
    ("s11_weblog", {"type": "Brute force", "location": "198.51.100.23",
                    "evidence": "many requests from one IP"}),
]

DECOYS = ["s04_clean", "s10_clean_auth", "s12_clean_weblog",
          "s15_clean_plugin", "s16_clean_crypto", "s17_clean_docsearch"]


def test_gold_matches_realistic_english_answers():
    for d, preds in GOOD_EN.items():
        assert _f1(d, preds) >= PASS_F1, f"{d}: 英語の正解回答が gold に当たらない"


def test_gold_matches_realistic_japanese_answers():
    for d, preds in GOOD_JA.items():
        assert _f1(d, preds) >= PASS_F1, f"{d}: 日本語の正解回答が gold に当たらない"


def test_gold_rejects_wrong_class_findings():
    for d, pred in BAD:
        gold = _gold(d)
        pt = _serialize(pred)
        assert not any(_covers(pt, g) for g in gold), f"{d}: 誤検出 {pred['type']} が gold を覆っている"


def test_decoys_have_empty_gold():
    for d in DECOYS:
        assert _gold(d) == [], f"{d}: デコイの gold が空でない"
        assert _f1(d, []) == 1.0
        assert _f1(d, [{"type": "made up", "location": "x", "evidence": "y"}]) == 0.0


def test_keywords_all_or_group_supported():
    """keywords_all のリスト要素が OR グループとして扱われること."""
    g = {"any_of": ["foo"], "keywords_all": [["travers", "トラバーサル"]]}
    assert _covers(_serialize({"type": "パストラバーサル", "evidence": "foo"}), g)
    assert _covers(_serialize({"type": "path traversal", "evidence": "foo"}), g)
    assert not _covers(_serialize({"type": "sql injection", "evidence": "foo"}), g)


# ── 実モデル出力からの回帰ケース ────────────────────────────────────
# GLM-5.3 が s05 に対して返した5件。コマンドインジェクション2件が TP、
# パストラバーサル2件と認証欠如1件は「副次的だが妥当」なので中立に落ちる。
GLM53_S05 = [
    {"type": "CWE-78 (OS Command Injection)",
     "location": "create_archive() — cmd construction and subprocess.run",
     "evidence": 'cmd = f"tar -czf {ARCHIVE_DIR}/{project_name}.tar.gz ..." subprocess.run(cmd, shell=True)'},
    {"type": "CWE-78 (OS Command Injection)",
     "location": "disk_usage() — subprocess.check_output with concatenated input",
     "evidence": 'subprocess.check_output("du -sh /srv/projects/" + project_name, shell=True)'},
    {"type": "CWE-20 / CWE-22 (Unvalidated Input leading to Path Traversal)",
     "location": "backup() — project parameter sourced from user-controlled form data",
     "evidence": 'project = request.form.get("project", "") ... create_archive(project)'},
    {"type": "CWE-22 (Path Traversal)",
     "location": "create_archive() — project_name used to build archive/source paths",
     "evidence": 'project="../../etc" archives /etc and writes outside ARCHIVE_DIR'},
    {"type": "CWE-306 (Missing Authentication for Sensitive Function)",
     "location": "/backup route handler backup()",
     "evidence": '@app.route("/backup", methods=["POST"]) (no auth check)'},
]


def test_s05_short_keyword_does_not_substring_match():
    """"rce" のような短い語が "sourced"/"source" に誤マッチしないこと (回帰)."""
    gold = _gold("s05_cmdinj")
    pred = {"type": "Path Traversal", "location": "backup()",
            "evidence": "project parameter sourced from user-controlled form data"}
    assert not any(_covers(_serialize(pred), g) for g in gold)


def test_s05_glm53_output_scores_full_marks():
    tp, neutral, fp = _classify("s05_cmdinj", GLM53_S05)
    assert (tp, neutral, fp) == (2, 3, 0)
    assert _f1("s05_cmdinj", GLM53_S05) == 1.0


def test_allow_extra_does_not_rescue_unrelated_findings():
    """allow_extra があっても無関係な指摘は FP のまま (逃がし弁が緩すぎないこと)."""
    junk = [{"type": "Buffer overflow", "location": "nowhere",
             "evidence": "zzz nonexistent qqq"}]
    for d in ["s05_cmdinj", "s08_idor", "s13_toctou", "s14_ssti_xss"]:
        tp, neutral, fp = _classify(d, junk)
        assert (tp, neutral, fp) == (0, 0, 1), f"{d}: 無関係な指摘が中立に落ちている"


def test_decoys_have_no_allow_extra():
    """デコイに逃がし弁を付けない (過検出の罰則を薄めないため)."""
    for d in DECOYS:
        assert _doc(d).get("allow_extra", []) == [], f"{d}: デコイに allow_extra がある"


# ── 2軸ゲート (pass_recall + max_fp_per_gold) の意味論 ──────────────
def _gate(recall: float, fp: int, n_gold: int,
          pass_recall: float = 0.6, max_fp_per_gold: float = 1.0) -> bool:
    return recall >= pass_recall and fp <= int(max_fp_per_gold * n_gold)


def test_gate_requires_majority_recall_without_boundary_accidents():
    """G=1→1/1, G=2→2/2, G=3→2/3, G=4→3/4。境界に厳密な分数が乗らない."""
    assert _gate(1 / 1, 0, 1) and not _gate(0 / 1, 0, 1)
    assert _gate(2 / 2, 0, 2) and not _gate(1 / 2, 0, 2)
    assert _gate(2 / 3, 0, 3) and not _gate(1 / 3, 0, 3)
    assert _gate(3 / 4, 0, 4) and not _gate(2 / 4, 0, 4)


def test_gate_tolerates_one_stray_finding_per_gold():
    assert _gate(1.0, 1, 1)        # gold1件+余分1件 → 合格 (旧 F1 0.667 で不合格だった)
    assert not _gate(1.0, 2, 1)
    assert _gate(1.0, 3, 3) and not _gate(1.0, 4, 3)


def test_gate_keeps_decoys_strict():
    assert _gate(1.0, 0, 0)        # 空配列だけが正解
    assert not _gate(1.0, 1, 0)    # 1件の誤検出で不合格
