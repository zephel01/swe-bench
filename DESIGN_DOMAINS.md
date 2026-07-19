# 🧭 マルチドメイン拡張 仕様書 (DESIGN_DOMAINS.md)

**版**: draft-1 / **対象**: llmbench に「コーディング以外の能力」を測る採点軸を追加する
**関連**: README.md（既存アーキテクチャ） / TASKS.md（タスク設計） / certify.py（tier認証）

---

## 1. 背景と目的

現行 llmbench は「隠しpytest → resolved(0/1)」という**客観オラクル**を入口に、その下流へ
pass@k・combined・usability・certify を積み上げている。この設計はコーディングにしか使えない。
一方でローカルLLMの実運用では、コード修正以外の能力が任せられるかを知りたい:

- **セキュリティ/解析** — ログやコードから既知の侵害・脆弱性を**検出・診断**できるか
- **一般タスク/指示追従** — 要約・抽出・整形・制約遵守。コーダー特化モデルの「一般退化」を測る
- **創作/文章生成** — リリースノート・説明文などの文章品質（最も客観化が難しい）

本拡張のゴールは、これらを**既存エンジンを壊さずに**測れるようにすること。

## 2. 設計原則 — pluggable grader

**核心**: 採点器 (grader) を差し替え可能にし、各採点器が最終的に
`(resolved: bool, quality: 0–100)` という**同じインターフェイスに正規化**して返す。
こうすれば `_aggregate_attempts` / `combined_score` / pass@k / usability / certify は
**一切変更不要**で再利用できる。`--with-l6/l7` が難易度の縦展開だったのに対し、本拡張は
**オラクルの横展開**である。

```
generate ─▶ grader.evaluate(task, output) ─▶ (resolved, quality, components, detail)
                                                │
                        既存の集計/信頼性/認証パイプライン（無改修）
```

grader は「出力契約（プロンプト）」と「採点」の両方を所有する:

```python
class Grader:
    name: str
    domain: str                                   # "code" | "security" | "general" | "writing"
    def build_prompt(task, lang) -> (system, user)   # 出力フォーマットの指示
    def evaluate(task, raw_output, ctx) -> GraderEval
    def mock_gold(task) -> str                     # validate用: 正解相当の出力
    def mock_broken(task) -> str                   # validate用: 失敗すべき出力
```

`GraderEval`（`Attempt` に写像される正規化結果）:

| フィールド | 型 | 意味 |
|---|---|---|
| `resolved` | bool | この試行が「成功」か（成功率・pass@k の素） |
| `quality_score` | float 0–100 | 採点品質（combined のスケーラ） |
| `parse_ok` / `parse_error` | bool / str | 出力パースの成否 |
| `parsed_files` | dict | artifacts 保存物（予測ラベル・回答など） |
| `fail_reason` | str | 失敗理由 |
| `components` | dict | 採点内訳（レポート表示。P/R/F1・チェック通過数など） |
| `detail_output` | str | 採点詳細テキスト（既存 `test_output` に相当） |

## 3. 採点器仕様

### 3.1 code（既存・ラップ）

現行の `parse_llm_output → evaluate_functional → evaluate_quality → combined_score` を
そのまま `CodeGrader` として包む。挙動・スコア・validate 結果は現状と完全一致（後方互換）。

### 3.2 detection（セキュリティ/解析）

**測るもの**: 検出・診断能力（修正ではなく「危険を正しく指摘できるか」）。

**出力契約**: モデルは `--- FINDINGS ---` の後に JSON 配列を出す。
各要素は `{"type": "...", "location": "...", "evidence": "..."}`。

```
--- FINDINGS ---
[
  {"type": "CWE-22 Path Traversal", "location": "line 42", "evidence": "open(os.path.join(base, user_path))"}
]
```

**gold.json**:

```json
{
  "findings": [
    {"id": "path_traversal", "cwe": "CWE-22",
     "any_of": ["os.path.join", "user_path", "../"],
     "keywords_all": ["travers"], "min_hits": 1}
  ]
}
```

- 予測 `p` が gold `g` を**カバー**: `p` の直列化テキスト（type+location+evidence を小文字化）が
  `g.any_of`（+ `g.cwe`）の**いずれか**を含み、かつ `g.keywords_all` を**すべて**含む。
- 予測 `p` が **真陽性(TP)**: いずれかの gold をカバー。そうでなければ **偽陽性(FP)**。
- `recall = カバーされたgold数 / gold総数`、`precision = TP予測数 / 予測総数`、`F1 = 2PR/(P+R)`。
- **デコイ（gold.findings == []）**: `recall=1`。予測0件→`precision=1`→F1=1（合格）、
  予測≥1件→`precision=0`→F1=0（過検出を罰する）。**過検出モデルはここで落ちる**のが要点。
- `resolved = F1 ≥ pass_f1`（既定 0.67, config `graders.detection.pass_f1`）。`quality = round(F1×100)`。

**validate**: `mock_gold` は gold.findings から FINDINGS を構築（デコイは `[]`）。
`mock_broken` は**架空の finding を1件**出す → デコイでは FP、非デコイでは recall0 で、
いずれも F1=0 → 失敗（broken 不変条件を満たす）。

### 3.3 constraint（一般タスク/指示追従・IFEval方式）

**測るもの**: 指示・制約の遵守。完全客観（judge 不要）。コーダー特化モデルの一般退化が可視化される。

**出力契約**: モデルは `--- ANSWER ---` の後に回答本文を出す（無ければ全文を回答とみなす）。

**checks.json**（プログラム検証可能なチェック配列）:

```json
[
  {"kind": "word_count", "min": 50, "max": 120},
  {"kind": "json_valid"},
  {"kind": "json_path", "path": "status", "equals": "ok"},
  {"kind": "regex", "pattern": "^- ", "flags": "m", "desc": "箇条書き"},
  {"kind": "contains", "text": "TODO", "ci": true},
  {"kind": "not_contains", "text": "```"},
  {"kind": "line_count", "max": 5}
]
```

対応 kind: `word_count` / `line_count` / `char_count`(min/max) / `contains` / `not_contains` /
`starts_with` / `ends_with` / `equals` / `regex`(negate可) / `json_valid` / `json_path`(equals)。

- `resolved = 全チェック通過`（instruction-strict accuracy）。
- `quality = 通過数 / 総数 × 100`（instruction-level accuracy）。IFEval の 2 指標に対応。
- **validate**: `mock_gold` は `gold_answer.md` を返す（全チェック通過するよう作成）。
  `mock_broken` は制約を破るテキスト → 失敗。

### 3.4 judge（創作/文章生成・実験的）

**測るもの**: 文章品質。**オラクルが無く rubric + judge 依存**のため **experimental 扱い**
（L7 と同じく未較正）。

**出力契約**: `--- ANSWER ---` の後に文章本文。

**rubric.json**:

```json
{
  "hard_constraints": [{"kind": "word_count", "min": 80, "max": 200}],
  "criteria": [
    {"name": "明確さ", "weight": 1.0, "desc": "主旨が一読で伝わる"},
    {"name": "網羅性", "weight": 1.0, "desc": "指定要素を漏れなく含む"}
  ],
  "pass_score": 7.0
}
```

- まず `hard_constraints`（constraint と同じ kind 群）を**決定的ゲート**として評価。
- judge クライアントがある場合: rubric で judge に 0–10 採点させ（`quality.judge.seeds` 回の平均、
  self-preference 回避のため judge≠候補モデル推奨）。`quality = score×10`、
  `resolved = (hard全通過) かつ (score ≥ pass_score)`。judge 一致のばらつきを `components` に残す。
- **judge クライアントが無い場合（validate/mock 含む）**: 決定的な hard_constraints のみで判定
  （`resolved = hard全通過`, `quality = 100/0`）。これで validate は決定的に緑を保てる。
- **validate**: `mock_gold` は `gold_answer.md`（hard 通過）→ 成功。`mock_broken` → 失敗。

## 4. タスク・ディレクトリ規約

```
tasks/
  s01_pathtrav/            # detection
    issue.md / issue_ja.md   #   指示文 + 解析対象（ログ/コードを本文に含める）
    gold.json                #   検出ラベル
  g01_json_summary/         # constraint
    issue.md / issue_ja.md   #   プロンプト
    checks.json              #   チェック配列
    gold_answer.md           #   validate用の合格回答
  w01_release_note/         # judge
    issue.md / issue_ja.md
    rubric.json
    gold_answer.md
```

コード系のような `buggy_code/` `gold/` `tests/` は不要。`tasks.py` は `buggy_code/` 欠落を許容する。

## 5. 台帳と CLI

新規台帳（既定では読まれない）: `tasks_sec.jsonl` / `tasks_gen.jsonl` / `tasks_write.jsonl`。
レコードに `grader` と `domain` と `difficulty` を持たせる:

```json
{"task_id":"s01","dir":"s01_pathtrav","grader":"detection","domain":"security","difficulty":"sec_medium","title":"..."}
{"task_id":"g01","dir":"g01_json_summary","grader":"constraint","domain":"general","difficulty":"gen_easy","title":"..."}
{"task_id":"w01","dir":"w01_release_note","grader":"judge","domain":"writing","difficulty":"write_basic","title":"..."}
```

CLI フラグ（`--with-l6/l7` と同じ体系）:

| フラグ | 意味 |
|---|---|
| `--with-sec` / `--with-gen` / `--with-write` | 既定40問に各ドメイン台帳を上乗せ |
| `--only-sec` / `--only-gen` / `--only-write` | 既定を除外し当該ドメインのみ実行（分割運用） |

`certify --merge` で分割実行結果を統合できる（既存機構をそのまま利用）。

## 6. certify 拡張 — ドメイン別 + バランス指数

コーディングの L1–L7 認証は不変。追加で:

- results の各タスクが持つ `domain` で集計し、**ドメイン別ゲート**を適用（`certify_domains`）。

| Domain | 既定 gate（暫定） | 備考 |
|---|---|---|
| security | success ≥ 0.6 かつ combined ≥ 60 | 検出は過検出も combined に反映 |
| general | success ≥ 0.7 かつ combined ≥ 65 | 指示追従は高めに |
| writing | success ≥ 0.5 かつ combined ≥ 55 | **experimental**（未較正） |

- **バランス指数**: 測定済み各ドメイン（coding 含む）の平均 combined を 0–1 に正規化し、
  **調和平均**で合成（弱いドメインに厳しい）。一芸特化スパイクを1枚で炙り出す。
  writing は experimental のため既定でバランス指数から除外（フラグで含めることは可）。
- 混ぜて単一平均にしない（コード満点が創作の低さを隠すのを防ぐ）。

## 7. config 追加

```yaml
graders:
  detection: {pass_f1: 0.67}
  constraint: {pass_ratio: 1.0}
  judge: {pass_score: 7.0}
quality:
  judge:
    enabled: false          # 別系統の judge を起動しているとき true
    judge_model: local-openai
    seeds: 1
certify_domains:
  security: {min_success: 0.6, min_combined: 60}
  general:  {min_success: 0.7, min_combined: 65}
  writing:  {min_success: 0.5, min_combined: 55, experimental: true}
```

## 8. 実装フェーズ

- **Phase 1（本仕様）**: grader フレームワーク + detection/constraint/judge、各ドメイン数問、
  CLI/certify/report/config 配線、validate 緑化。judge は experimental。
- **Phase 2（将来）**: 実モデル較正でドメインゲート確定、judge の多系統化と一致率の本採用、
  各ドメインの sub-tier 化（sec_easy/…/sec_hard を独立 gate に）、タスク増補（各20–40問）。

## 9. 後方互換性

- `grader` 未指定のレコードは `code` 既定 → 既存タスクは無改修で従来通り。
- 既定台帳（`tasks.jsonl`）だけの実行は結果・validate・スコアが現状と一致する。
- 新規フィールド（`domain` 等）は results.json に増えるだけで、既存 `certify`/`compare` は無視して動く。
