# 🛠️ llmbench 運用マニュアル（artifacts / 信頼性 / usability / 比較 / モデル解決）

本書は、artifacts保存・レポート刷新に加え、その後追加された **信頼性(pass@k)・usability判定・
モデル横断比較・モデル解決(model:auto/Ollama動的)** までを、「運用・保守・他システム連携」の
観点でまとめた**運用＆リファレンスマニュアル**です。

ドキュメントの役割分担：

| ドキュメント | 対象読者 | 内容 |
|---|---|---|
| [README.md](../README.md) | はじめての人 | 概要・特徴・スコア定義・タスク追加 |
| [USAGE.md](USAGE.md) | 利用者 | 実行手順と結果の**読み解き方** |
| [CHANGES.md](CHANGES.md) | 全員 | 追加機能の要約と変更履歴 |
| **本書（運用マニュアル）** | 運用・保守・連携担当 | 出力ファイルの**仕様**・内部実装・運用上の注意・移行・自動化 |

> 対象バージョン: 既定40タスク(L1-L5) + 任意L6 architect 20タスク(`--with-l6`/単体実行`--only-l6`) + 任意L7 grandmaster **16タスク**(v2。`--with-l7`/単体実行`--only-l7`。旧40問は `--l7-ledger tasks_l7_v1.jsonl` で実行可)・多試行(pass@k)・usability・compare・certify(L1-L7、`certify --merge`で分割結果を統合)・`model:auto` 対応版。
> `results.json` に `summary.usability` / `success_rate` 等を含む。

---

## 目次

1. [新規追加機能の全体像](#1-新規追加機能の全体像)
2. [出力ファイル仕様（リファレンス）](#2-出力ファイル仕様リファレンス)
3. [内部実装リファレンス（保守者向け）](#3-内部実装リファレンス保守者向け)
4. [運用上の注意（ディスク・保持・git）](#4-運用上の注意ディスク保持git)
5. [自動化・CI連携](#5-自動化ci連携)
6. [プログラムからの結果アクセス](#6-プログラムからの結果アクセス)
7. [移行メモ（旧形式との差分）](#7-移行メモ旧形式との差分)
8. [変更ファイル早見表](#8-変更ファイル早見表)
9. [追加サブシステム（信頼性・usability・比較・モデル解決）](#9-追加サブシステム信頼性usability比較モデル解決)
10. [マルチドメイン評価（グレーダー拡張）](#10-マルチドメイン評価グレーダー拡張)
11. [クラウドLLM（ホスト型API）の評価手順](#11-クラウドllmホスト型apiの評価手順)

---

## 1. 新規追加機能の全体像

今回の変更は「スコアが出る」だけだった旧版に対し、
**「なぜそのスコアなのかをコードまで遡って確認できる」** ことを目的に、次の3点を追加しました。

| # | 機能 | 目的 | 主な実装 |
|---|---|---|---|
| ① | **生成物（artifacts）の永続保存** | 失敗・低スコアの原因をコードレベルで追える | `runner.py`: `_write_artifacts()` |
| ② | **レポートの刷新** | サマリ表・タスク別詳細・読める品質内訳 | `report.py`: `render_markdown()` ほか |
| ③ | **実行ログの強化** | 実行中にその場で「動いているか」を把握 | `runner.py`: `_log_task()` / `_snippet()` |

副次的に、`results.json` は集計・スコア中心の**軽量JSON**に保たれるよう、
大きい生成物フィールドを別ディレクトリ（artifacts）へ分離しています。

その後さらに、「**実際どれくらい使えるか**」を測るための機能群を追加しました
（詳細は **9章**、要約は `CHANGES.md`）:

| # | 機能 | 目的 |
|---|---|---|
| ④ | **信頼性 (pass@k / `--runs`)** | 1回成功ではなく、安定して成功するかを成功率で測る |
| ⑤ | **usabilityティア** | スコアを🟢自律/🟡補助/🔴不可の運用判断に翻訳 |
| ⑥ | **モデル横断比較 (`compare`)** | 参照モデルと並べて位置づけ |
| ⑦ | **モデル解決 (`model:auto` / Ollama動的)** | config編集なしでモデルを差し替え |
| ⑧ | **難タスク t016–t020** | 失敗が出る実務的タスクで識別力を確保（既定40タスク） |

---

## 2. 出力ファイル仕様（リファレンス）

1回の `run` で、出力先（既定 `results/`）に **3種類** が生成されます。
`<stamp>` は実行時刻（`YYYYMMDD_HHMMSS`）、`<model>` は `--model` のキー名です。

```
results/
├── <stamp>_<model>_results.json      # ① 集計・スコア（機械可読・軽量）
├── <stamp>_<model>_report.md         # ② 人が読むレポート
└── <stamp>_<model>_artifacts/        # ③ 生成物（★新規）
    └── <task_id>/
        ├── llm_output.txt            #   LLMの生出力
        ├── generated/<path>          #   適用された生成コード
        └── test_output.txt           #   pytest出力
```

### 2.1 `results.json` スキーマ（軽量JSON）

トップレベル：

| キー | 型 | 説明 |
|---|---|---|
| `model` | str | モデルラベル。`model:auto`時はサーバ検出名、`--label`で上書き可 |
| `issue_lang` | str | `en` / `ja` |
| `artifacts_dir` | str | 対応するartifactsディレクトリ名（相対） |
| `served_model` | str | 任意。`model: auto` または `type: cli` で実モデルが検出できたときのみ出力される実モデル名 |
| `summary` | obj | 下表 |
| `results` | array | タスクごとの結果（下表） |

`summary`：

| キー | 説明 |
|---|---|
| `resolved_rate` | resolved 割合（0.0–1.0、小数3桁）。多試行では success_rate≥0.5 を resolved とみなす |
| `avg_quality_resolved` | **resolvedタスクのみ**の品質平均（小数1桁） |
| `avg_combined` | 全タスクのcombined平均（小数1桁） |
| `n_tasks` | タスク数 |
| `runs` | 1タスクあたりの試行回数 |
| `usability` | `{autonomous, assisted, unusable}` のタスク数 |
| `n_refused_tasks` / `n_refused_attempts` | セーフティ拒否があったタスク数 / 拒否試行の総数。0 でないランは「知らない」と「答えない」が混ざっている |
| `avg_success_rate` | 平均成功率（=平均pass@1）。**多試行時のみ** |
| `solved_any_rate` | N回中≥1成功したタスクの割合。**多試行時のみ** |
| `avg_pass_at_k` | 平均pass@k。**多試行時のみ**（k=runsで退化する点に注意） |

`results[]`（**軽量化済み** — 大きいフィールドは除外）：

| キー | 型 | 説明 |
|---|---|---|
| `task_id` | str | 例: `t001` |
| `difficulty` | str | 台帳の `difficulty` をそのまま転記する自由文字列。コーディング7値（`easy` / `medium` / `hard` / `expert` / `frontier` / `architect` / `grandmaster`）+ ドメイン用11値（`sec_medium` / `sec_hard` / `gen_easy` / `gen_medium` / `write_basic` / `med_basic` / `med_std` / `med_hard` / `cul_knowledge` / `cul_completion` / `cul_generation`）の計18値。tier への対応は `certify.py` の `DIFFICULTY_TO_TIER` が正 |
| `title` | str | タスクタイトル |
| `domain` | str | `code` / `security` / `general` / `writing` / `medical` / `culture` / `uncensored`。既定 `"code"` |
| `resolved` | bool | テスト合格判定（多試行では success_rate≥0.5） |
| `quality_score` | float | 0–100。多試行では**成功試行の平均** |
| `combined` | float | 0–100。`success_rate × (floor + (1-floor)×quality/100) × 100` |
| `latency_sec` / `tokens_per_sec` / `completion_tokens` | — | 速度メトリクス（多試行は平均） |
| `fail_reason` | str | 失敗理由。部分成功は `flaky c/N passed` |
| `parse_ok` / `parse_error` | bool/str | 代表試行のパース成否・理由 |
| `runs` / `n_pass` | int | 試行回数 / 成功回数 |
| `success_rate` / `pass_at_1` / `pass_at_k` | float | 成功率（=pass@1）/ pass@k |
| `n_refused` / `refused` | int/bool | セーフティ拒否と判定された試行数 / 1回でも拒否があったか。**`resolved`・`success_rate` には影響しない**（不正解の内訳）。判定は不正解時のみ実施 |
| `attempts` | array | 各試行の `{resolved, quality, combined, fail_reason, truncated, finish_reason, errored, skipped, refused}` |
| `usability_tier` | str | `autonomous` / `assisted` / `unusable` |
| `quality_components` | obj | 代表試行の ruff / complexity / … 内訳 |

> ⚠️ **`results.json` に含まれないフィールド**（artifactsへ分離）:
> `raw_output`（LLM生出力）・`parsed_files`（生成コード）・`test_output`（pytest出力）。
> これらは `ARTIFACT_FIELDS` として `save_run()` の `_lean()` で除外されます。
> `changed_files` はプロパティのためJSONには出力されません（artifacts側の `generated/` で確認）。

### 2.2 `report.md` の構成

刷新後の構成は **サマリ → usability判定 → タスク別結果 → 難易度別 → ドメイン別（該当時） → タスク別詳細**。

- **サマリ**: Resolved率（n/N）・品質平均・Combined平均を表形式。`artifacts_dir` がある場合は保存先を注記。
- **usability判定**: サマリ直下に🟢自律/🟡補助/🔴不可のティア集計・難易度×ティアの割合・保守的な総合推奨を出力。
- **タスク別結果（一覧表）**: 先頭列が ✅/❌ アイコン、**判定（ティア）**列、**生成ファイル**列と**備考**列（失敗理由・パースエラー）を追加。多試行時は**信頼性**列も追加。
- **難易度別**: 難易度（**7段階**: easy/medium/hard/expert/frontier/architect/grandmaster）ごとの resolved 数と品質平均。
- **ドメイン別（該当時）**: コーディング以外の grader が混在する場合のみ、domain ごとの Resolved・平均成功率・平均combinedを表示。
- **タスク別詳細**: タスクごとに難易度・判定・usability・生成ファイル・生成物パス・**整形済み品質内訳**（ruff/complexityを日本語で説明）。

### 2.3 `artifacts/<task_id>/` ディレクトリ契約

| パス | 生成条件 | 中身 |
|---|---|---|
| `llm_output.txt` | `raw_output` が非空のとき | LLMが返した生テキスト全体 |
| `generated/<相対パス>` | パース成功ファイルごと | 適用された生成コード（末尾改行は正規化） |
| `test_output.txt` | `test_output` が非空のとき | pytestの出力（成功時stdout / 失敗時stdout+stderr） |

> 📌 **失敗実行も保存される**: パース失敗タスクは `generated/` が空になり、`llm_output.txt` のみ残ります
> （＝原因調査ができる）。タスクディレクトリ自体は全タスク分作成されます。

---

## 3. 内部実装リファレンス（保守者向け）

### 3.1 `runner.py`

- **`TaskResult` の新フィールド**: `title` / `parse_ok` / `parse_error` / `parsed_files` / `raw_output` / `test_output`、
  および `changed_files`（`parsed_files` のキー一覧を返すプロパティ）。
- **`ARTIFACT_FIELDS = ("raw_output", "parsed_files", "test_output")`**:
  `save_run()` 内の `_lean()` がこの3つを `asdict()` 結果から `pop` し、JSONを軽量化。
- **`_run_task()`**: 生成直後に `raw_output` を、パース結果（`parse_ok`/`parse_error`/`parsed_files`）を、
  機能評価後に `test_output` を `TaskResult` へ記録。
- **`_write_artifacts(run, artifacts_dir)`**: タスクごとに `llm_output.txt` / `generated/<path>` / `test_output.txt` を書き出す。
- **`_log_task(progress, tr)` / `_snippet(text, n)`**: 実行ログを整形出力（生成ファイル・LOC・コード冒頭・テスト失敗末尾3行）。
- **`save_run()`**: `<stamp>_<model>_artifacts` を作り `_write_artifacts()` を呼び、`run.artifacts_dirname` を設定。
  `results.json`（lean）と `report.md` を書き出す。

### 3.2 `report.py`

| 関数 | 役割 |
|---|---|
| `render_markdown(run)` | レポート全体を組み立て |
| `_fmt_ruff(c)` | ruff内訳を整形（指摘なし／件数・密度・ルール・score） |
| `_fmt_complexity(c)` | complexity内訳を整形（MI・最悪CCランク・最複雑関数） |
| `_fmt_component(name, c)` | レイヤー名で整形関数を振り分け（汎用フォールバックあり） |
| `_status_icon(r)` | resolved を ✅/❌ に変換 |

### 3.3 ログ出力フォーマット（`_log_task`）

```
[3/40] t003 (easy) add_tag leaks tags across calls
    生成OK  files=[tags.py]  187tok @ 118.4tok/s
      └ tags.py (9 LOC): def add_tag(tag, tags=None): ⏎ if tags is None:
    ✅ RESOLVED  quality=100 combined=100  [🟢 自律]  (1.2s)
```

- パース失敗時は `生成パース失敗: <理由>` と `出力プレビュー:`（生出力冒頭）を表示。
- テスト失敗時は `| ...` で pytest 出力末尾3行を表示。

---

## 4. 運用上の注意（ディスク・保持・git）

### 4.1 ディスク使用量

artifacts は**実行ごと**に `llm_output.txt`（生出力全文）・`generated/`・`test_output.txt` を保存します。
タスク数 × モデル × 試行回数の分だけ蓄積されるため、定期的な掃除を推奨します。

```bash
# 出力先全体のサイズ確認
du -sh results/*

# 直近5実行のみ残して古いものを削除（例）
ls -dt results/*_artifacts | tail -n +6 | xargs rm -rf
ls -t  results/*_results.json | tail -n +6 | xargs rm -f
ls -t  results/*_report.md   | tail -n +6 | xargs rm -f
```

### 4.2 `.gitignore`

実行結果はリポジトリに含めないのが基本です。リポジトリの `.gitignore` に
`results/` 系が含まれているか確認してください（生出力にプロンプト全文が残るため、共有時は内容に注意）。

```gitignore
results/
*_artifacts/
```

### 4.3 元タスクの不変性

artifacts への書き込みは出力先ディレクトリ配下のみ。タスク定義（`tasks/`）や元ソースは一切変更されません
（パッチ適用は一時workspaceに対してのみ実行）。

---

## 5. 自動化・CI連携

### 5.1 パイプライン健全性ゲート（`validate`）

LLM接続不要のモック検証。CIの前段ゲートに使えます。

```bash
llmbench validate            # PASS で exit 0 / FAIL で exit 1
```

- mock-gold が全タスク resolved、mock-broken が全タスク fail、broken combined平均=0 のとき `VALIDATION: PASS`。

### 5.2 複数モデル比較

```bash
llmbench run --model local-openai --output results
llmbench run --model local-ollama --output results

for f in results/*_results.json; do
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); \
    s=d['summary']; print(f\"{d['model']:24s} resolved={s['resolved_rate']*100:5.1f}%  \
combined={s['avg_combined']:.1f}  quality={s['avg_quality_resolved']:.1f}\")" "$f"
done
```

`results.json` は軽量（生出力を含まない）ため、CIアーティファクトとして保管しても軽量です。
詳細調査が必要なときだけ対応する `*_artifacts/` を併せて保管します。

---

## 6. プログラムからの結果アクセス

### 6.1 `jq` での集計例

```bash
# 失敗タスクのIDと理由を列挙
jq -r '.results[] | select(.resolved|not) | "\(.task_id)\t\(.fail_reason)"' \
  results/<stamp>_<model>_results.json

# パース失敗だけ抽出
jq -r '.results[] | select(.parse_ok|not) | "\(.task_id)\t\(.parse_error)"' \
  results/<stamp>_<model>_results.json

# artifactsディレクトリ名を取得し、失敗タスクの生出力を開く
adir=$(jq -r '.artifacts_dir' results/<stamp>_<model>_results.json)
cat "results/$adir/t011/llm_output.txt"
```

### 6.2 失敗原因の追い方（フロー）

| 症状 | 見るファイル | 分かること |
|---|---|---|
| `parse_ok=false` | `artifacts/<id>/llm_output.txt` | `--- FILE: path ---`＋コードブロック形式の崩れ |
| `fail_reason=tests failed` | `artifacts/<id>/test_output.txt` → `generated/` | 落ちたassert → 該当ロジック誤り |
| `fail_reason=timeout` | `test_output.txt` | 無限ループ等。`run.test_timeout` の見直し |
| 品質が低い | `generated/<path>` | ruff指摘・複雑な関数を実コードで確認 |

---

## 7. 移行メモ（旧形式との差分）

旧版の出力をパースしている既存スクリプトがある場合、次の差分に注意してください。

### 7.1 `results.json`

- **追加**: トップレベル `artifacts_dir`、各 result に `title` / `parse_ok` / `parse_error`。
- **削除（lean化）**: result から `raw_output` / `parsed_files` / `test_output` は**出力されません**（artifactsへ移動）。
  これらをJSONから読んでいたスクリプトは、artifactsファイル参照へ切り替えが必要です。

### 7.2 `report.md`

- **タスク別結果テーブルの列構成が変更**されました。
  - 旧: `| Task | 難易度 | Resolved | Quality | Combined | 生成時間(s) | tok/s | 失敗理由 |`（8列、先頭=Task）
  - 新: `| | Task | 難易度 | 判定 | 生成ファイル | Quality | Combined | 生成時間 | tok/s | 備考 |`（10列、先頭=✅/❌アイコン）。
    多試行時は「判定」の後に**信頼性**列が入り11列になる。
  - Resolved の `O/X` は ✅/❌ に変更。Markdownテーブルを機械パースしている場合は要修正。
- セクション見出し `## 品質内訳 (タスク別)` は `## タスク別詳細` に変更。

### 7.3 `config.yaml`

- サンプルの `local-openai` が `base_url: http://localhost:8085/v1` / `model: "auto"` に更新
  （実際の config.yaml 実値。`auto` はサーバのロード中モデルを自動採用するため、ggufを差し替えても
  config編集不要）。これは設定例の変更であり挙動には影響しません。**結果ファイル名は `--model` のキー名**
  （`local-openai`）で決まるため、キー名を変えない限りファイル名は安定します。

---

## 8. 変更ファイル早見表

| ファイル | 変更概要 |
|---|---|
| `llmbench/runner.py` | artifacts保存 + **多試行集計**（`Attempt`/`_aggregate_attempts`/pass@k）・**モデル解決**（`resolve_model`/Ollama自動・`model:auto`ラベル）・`_log_task` |
| `llmbench/scoring.py` | `combined_score` を success_rate スケールに一般化 + `pass_at_k`（不偏推定量） |
| `llmbench/usability.py` | **新規**。ティア分類 `classify()` と集計 `aggregate()` |
| `llmbench/compare.py` | **新規**。複数 results.json の横断比較レポート |
| `llmbench/report.py` | usability判定セクション・信頼性列・pass@1主指標・保守的な総合推奨・品質内訳注記 |
| `llmbench/clients/openai_compat.py` | `model:auto` のサーバ検出（`fetch_served_model`）・APIキー環境変数展開 |
| `llmbench/clients/ollama.py` | `list_ollama_models()`（`/api/tags`） |
| `llmbench/cli.py` | `models` / `compare` / **`certify`** サブコマンド・`--runs`/`--sample-temp`/**`--concurrency`**/`--label`/`--ollama-host`・**`--with-l6`/`--l6-ledger`**・**`--with-l7`/`--l7-ledger`**・**`--only-l6`/`--only-l7`（list-tasks/run/validate共通の`_common_args`）**・**`certify --merge`** |
| `llmbench/certify.py` | **新規**。難易度→tier(L1-L7)、tier別gate判定（`certify`/`render_certificate_md`）。使えるライン=L4独立合格・**architect→L6 gate**・**grandmaster→L7 gate（暫定・天井評価用）**・**`merge_results()`（複数results.jsonの合算。task_id後勝ち・model名を出現順distinctで` + `連結）/ `certify --merge`（単体スクリプトでも`python3 certify.py --merge`で対応）** |
| `llmbench/tasks.py` | `Task.perf_timeout` フィールド・**`load_tasks(..., ledgers=[...])` で複数台帳マージ（id先勝ち）** |
| `llmbench/runner.py` | per-task `perf_timeout` を採用（未指定時は `test_timeout`）・**`BenchmarkRunner(..., ledgers=...)`** |
| `config.yaml` | `model:auto`・`run.runs`/`sample_temp`/`ollama_host`・`usability:`・`ref-gpt` |
| `tasks/` | 難タスク t016–t020 + **L4 expert t021–t032 / L5 frontier t033–t040**（既定40タスク）+ **L6 architect t041–t060（別台帳 `tasks_l6.jsonl`・`--with-l6` で有効化）** + **L7 grandmaster 現行16問（別台帳 `tasks_l7.jsonl`・`--with-l7` で有効化。v1残留9問（t063, t064, t068, t069, t076, t085, t092, t093, t095）+ 新規7問（t101–t107。3多重oracle 4問 + 大規模リファクタ/仕様推論 3問）。旧40問（5軸×8問構成。t098のみ `perf_timeout: 30`）は `tasks_l7_v1.jsonl` に退避、`--l7-ledger tasks_l7_v1.jsonl` で実行可）** |
| `llmbench/clients/cli_agent.py` | **新規**。`type: cli` バックエンド（サブスクCLI: `claude`/`codex`/`grok`/`custom` プリセット）。空の一時cwdでheadless実行し、実行モデルを検出して `served_model` に記録 |
| `llmbench/graders/` | **新規パッケージ**（マルチドメイン評価）。`__init__.py`（グレーダーレジストリ + `GradeCtx`/`GraderEval`）・`checks.py`（IFEval式チェック群）・`code.py`（既存パイプラインのラップ）・`detection.py`（security）・`constraint.py`（general）・`judge.py`（writing・experimental）・`qa.py`（medical・reference value）・`refusal.py`（セーフティ拒否の検出。qa/constraint/judge から呼ばれ、**不正解時のみ**判定して `GraderEval.refused` を立てる）。各グレーダーは `(resolved, quality)` に正規化して返すため、既存の集計/pass@k/usability/certifyパイプラインは無改修 |
| `llmbench/cli.py`（マルチドメイン） | **`--with-sec/gen/write/med/culture/unc`・`--only-sec/gen/write/med/culture/unc`**（`--with-l6/l7`と同体系。list-tasks/run/validate共通の`_common_args`を拡張） |
| `llmbench/certify.py`（マルチドメイン） | **ドメイン別ゲート**（`certify_domains`）・**バランス指数**（coding＋非experimentalドメインの調和平均）・**医療の難易度別(med_basic/med_std/med_hard)正答率readout**・**過剰拒否の種別別(unc_knowledge/unc_procedure/unc_explain)正答率+拒否率readout**（`certify_uncensored`） |
| `llmbench/runner.py`（マルチドメイン） | **`JudgeSet`**（ドメイン別 judge 上書き。`quality.judge.domain_overrides` を `enabled` から独立に発火。`_make_judges()`/`_make_judge()`後方互換ラッパ） |
| `llmbench/report.py`（マルチドメイン） | **「🌐 ドメイン別」**サマリ節を追加 |
| `config.yaml`（マルチドメイン） | **`graders:`**（pass_f1/pass_ratio/pass_score）・**`quality.judge:`**（enabled/judge_model/seeds/**domain_overrides**）・**`certify_domains:`**・**`certify_uncensored:`**・参照モデル**`uncensored-ref`** |
| `tasks/`（マルチドメイン） | **ドメインタスク追加**: security s01–s04（別台帳`tasks_sec.jsonl`、`--with-sec`）/ general g01–g03（`tasks_gen.jsonl`、`--with-gen`）/ writing w01–w02（`tasks_write.jsonl`、`--with-write`）/ medical m01–m24（`tasks_med.jsonl`、`--with-med`。難易度 med_basic7/med_std11/med_hard6、全問ファクトチェック済）/ culture c01–c24（`tasks_culture.jsonl`、`--with-culture`。日本のネットミーム知識。cul_knowledge12/cul_completion6/cul_generation6、grader は qa/constraint/judge を流用）/ uncensored u01–u05（`tasks_unc.jsonl`、`--with-unc`。過剰拒否 (over-refusal) 検査。unc_knowledge2/unc_procedure2/unc_explain1、grader は qa/constraint/judge を流用。詳細は `DESIGN_UNCENSORED.md`） |

> 検証状況: `llmbench validate` PASS（gold 40/40・broken 40/40）、selfcheck 既存20問 + **L6 20問 20/20** + **L7 16問 16/16**（v2。旧40問時代の記録は `TASKS.md` の「L7 v1」節を参照）、
> `validate --with-l6` で gold 20/20・broken 20/20、`validate --with-l7` で gold 16/16・broken 16/16、
> `list-tasks` 40（既定）/ 60（`--with-l6`）/ 56（`--with-l7`）/ 76（`--with-l6 --with-l7`）/
> 20（`--only-l6`）/ 16（`--only-l7`）/ 36（`--only-l6 --only-l7`）、
> 多試行集計・usability・compare・certify・モデル解決の各単体、ruff（指摘ゼロ）、`compileall` を確認済み。
> 追加検証（マルチドメイン）: `llmbench validate --only-sec|gen|write|med|culture|unc` が全てPASS（gold全成功・broken全失敗、LLM不要）。詳細は10章。

---

## 9. 追加サブシステム（信頼性・usability・比較・モデル解決）

artifacts導入後に加わった主要機能の運用リファレンス。利用手順は `USAGE.md`、要約は `CHANGES.md`。

### 9.1 信頼性 (pass@k)

`--runs N`（または `run.runs`）で各タスクをN回サンプリング。`runner._aggregate_attempts()` が
成功率(=pass@1)・pass@k・代表試行を集計する。`scoring.pass_at_k(n,c,k)` は Chen et al. 2021 の不偏推定量。
**注意**: 本ハーネスは n=runs サンプルなので、`pass_at_k`（k=runs）は「N回中≥1成功」に退化する。
運用上の主指標は **success_rate(pass@1)**、補助に **solved_any_rate** を見ること。

### 9.2 usabilityティア

`usability.classify(success_rate, quality, cfg)` が 🟢自律 / 🟡補助 / 🔴不可 を返す。しきい値は
`config.yaml` の `usability:`。レポートは難易度×ティアの**割合**と、🔴不可を隠さない**保守的な総合推奨**を出す。

### 9.3 モデル比較 `compare`

`llmbench compare <results.json...>` → `comparison_<stamp>.md`。ランキング（最良比の相対スコア）・
ティア比較・タスク別Combinedマトリクスを生成。参照アンカーとして API モデル（`ref-gpt`）を併走させる。

### 9.4 モデル解決（config編集レス運用）

- `model: auto` … `openai_compat.fetch_served_model()` が `/v1/models` からロード中モデルを取得。
  ラベル（レポート/ファイル名）も実モデル名（`runner._label_from_model` で `.gguf` 除去）。
- Ollama動的 … config未定義の `--model <名前>` は `runner.resolve_model()` が `/api/tags` から解決。
- 接続先優先順 (Ollamaホスト): `--ollama-host` > env `OLLAMA_HOST` > config の ollama モデル `base_url` > `http://localhost:11434`。
- 接続先優先順 (base_url): `--base-url` > config `base_url` (`${VAR}` 展開可) > 型別 env (`OPENAI_BASE_URL` / `OLLAMA_HOST` / `CODEROUTER_BASE_URL`) > 型別デフォルト。
- `--client-type openai|ollama|multiagent` で config 未定義でも直接接続できる
  (例: `llmbench run --model auto --client-type openai --base-url http://localhost:8085/v1` で llama.cpp 直結、
   `--client-type multiagent --base-url http://localhost:8088` で CodeRouter)。
- `model: auto` は複数モデルロード時に `auto_prefer: "<部分文字列>"` で選択可能。未指定なら先頭を採用し警告を表示。
- 未設定の `${VAR}` 参照は明確なエラーになる (旧: 無警告で空文字 → 分かりにくい401)。
- `--label` で明示固定。APIキーは `${VAR}` を環境変数展開。

### 9.5 運用上の注意

- **多試行はディスク/時間が N 倍**。artifactsは代表1試行のみ保存するので肥大化は限定的だが、生出力は残る。
- pass@k の解釈は 9.1 の通り。`avg_pass_at_k` を「汎化性能」と誤読しないこと。
- レポート表の列数が増えている（判定・信頼性列）。機械パースは要追従（7章の移行メモ参照）。

### 9.6 L7 v1/v2 切替運用（`--l7-ledger`）

2026-07-21 に L7 grandmaster は 40問(v1) から 16問(v2) へ差し替えられた。既定の `--with-l7` /
`--only-l7` は現行台帳 `tasks/tasks_l7.jsonl`（v2・16問）を使うが、`--l7-ledger` で参照する
台帳ファイルを差し替えることで旧40問(v1)を再測定したり、過去のv1結果と継続比較したりできる。

```bash
# 旧40問(v1)で再測定する場合
llmbench run --model local-openai --with-l7 --l7-ledger tasks_l7_v1.jsonl

# validate も同様にv1台帳へ切替可能
llmbench validate --with-l7 --l7-ledger tasks_l7_v1.jsonl
```

- **過去のv1結果との継続比較**: v1時代に取得した `results.json`（L7が40問構成のもの）は、
  `certify --merge` では task_id が重複しないため v2結果とそのまま合算はできない。比較したい
  場合は `compare` で両者を横に並べるか、`--l7-ledger tasks_l7_v1.jsonl` で同一モデルを
  v1構成で再測定してから旧結果と突き合わせる。
- v1残留9問（t063, t064, t068, t069, t076, t085, t092, t093, t095）は両台帳に同じ内容で
  存在するため、task_id ベースでの部分比較は可能。
- v1のtier gate（pass@1 ≥ 0.35 / combined ≥ 55）は当時のまま16問版でも暫定的に流用されて
  おり、**v2向けの再較正は未実施**。v1台帳で測る場合もこの暫定gateが適用される。
- 詳細な旧40問の設計（5軸×8問）は `TASKS.md` の「L7 v1（退避済み・t061–t100）」節を参照。

---

## 10. マルチドメイン評価（グレーダー拡張）

コーディング専用だった評価を、**採点器(grader)を差し替え可能**にすることで他能力へ横展開した機能です。
設計の詳細（採点式・出力契約・validate仕様）は [📐 DESIGN_DOMAINS.md](DESIGN_DOMAINS.md) を参照してください。
本章は運用・保守観点のリファレンスです。利用手順は `USAGE.md`、要約は `CHANGES.md`。

### 10.1 grader の仕組みと後方互換性

各 grader は `build_prompt()`（出力フォーマットの指示）と `evaluate()`（採点）を持ち、結果を
`GraderEval`（`resolved: bool` / `quality_score: 0-100` / `components` / `fail_reason` など）に
**正規化**して返す。この正規化のおかげで `_aggregate_attempts` / `combined_score` / pass@k /
usability / certify は**一切変更せず**再利用される。

- 台帳レコードに `grader` フィールドが**無い**場合は `code`（既存パイプラインのラップ）が既定。
- 既定台帳 `tasks.jsonl` のみを実行した場合の結果・スコア・`validate` 判定は**従来と完全一致**する。
- パッケージは `llmbench/graders/`（`__init__.py` = レジストリ + `GradeCtx`/`GraderEval`、`checks.py`、
  `code.py`、`detection.py`、`constraint.py`、`judge.py`、`qa.py`）に新設。

### 10.2 5ドメインの概要

| domain | grader | 台帳 | フラグ | 採点方式 |
|---|---|---|---|---|
| security | `detection` | `tasks_sec.jsonl` | `--with-sec` / `--only-sec` | `--- FINDINGS ---` 後のJSON配列をgoldラベルと precision/recall/**F1** で採点。`resolved = F1 ≥ pass_f1`（既定0.67）。`gold.findings` が空の**クリーンなデコイ**タスクで過検出(precision低下)を罰する |
| general | `constraint` | `tasks_gen.jsonl` | `--with-gen` / `--only-gen` | `--- ANSWER ---` 後の回答を `checks.json`（IFEval式: word_count/line_count/char_count/contains/not_contains/starts_with/ends_with/equals/regex/json_valid/json_path）で機械検証。`resolved = 全チェック通過`（`pass_ratio` 既定1.0）、`quality = 通過率×100` |
| writing | `judge` | `tasks_write.jsonl` | `--with-write` / `--only-write` | **experimental**。`rubric.json` の `hard_constraints`（決定的ゲート、checkと同種kind）+ `criteria` + `pass_score`。judgeモデル設定時（`quality.judge.enabled`）は0-10点を`seeds`回平均し `quality=score×10`、`resolved=(score≥pass_score) かつ hard通過`。judge未設定時は `hard_constraints` のみで決定的判定（validate等はこの経路） |
| medical | `qa` | `tasks_med.jsonl` | `--with-med` / `--only-med` | **参考値**。`gold.json` は `{"mode":"mcq","answer":"C"}`（選択肢一致）または `{"mode":"keyword","all":[...],"any":[...]}`（`all`を全て・`any`を1つ以上含む）。gold keywordは**日英両方**を含むため `--lang ja` の日本語モデルも正しく採点される |
| culture | `qa`+`constraint`+`judge` | `tasks_culture.jsonl` | `--with-culture` / `--only-culture` | **参考値**。日本のネットミーム／ネットスラング（淫夢語録・なんJ・2ch・空耳ネタ）を **A.知識QA(`qa`, 12問) / B.補完・認識(`constraint`, 6問) / C.生成(`judge`, 6問)** の3層で測る。専用graderは持たず既存3種を流用し、台帳側で `domain: "culture"` を明示する。正答率とは**別に拒否率**を集計する（10.7参照） |
| uncensored | `qa`+`constraint`+`judge` | `tasks_unc.jsonl` | `--with-unc` / `--only-unc` | **参考値**。無害で正解が確定する質問に、過剰拒否を誘発する語や枠組み（kill / disposal of drugs / traversal / lock / chemical weapons 等）を添えて出題する over-refusal (XSTest/OR-Bench 系) ベンチ。**A.事実QA(`qa`, 2問) / B.手順・仕組み(`constraint`, 2問) / C.説明生成(`judge`, 1問)** の3層で測る。専用graderは持たず既存3種を流用し、台帳側で `domain: "uncensored"` を明示する。jailbreak ベンチではなく、有害な要求への応諾は測らない。正答率とは**別に拒否率**を集計する（10.7参照）。詳細設計は `DESIGN_UNCENSORED.md` |

### 10.3 CLI

`--with-l6`/`--with-l7`/`--only-l6`/`--only-l7` と同じ体系です。

- `--with-sec` / `--with-gen` / `--with-write` / `--with-med` / `--with-culture` / `--with-unc` … 既定タスクにドメイン台帳を上乗せ
- `--only-sec` / `--only-gen` / `--only-write` / `--only-med` / `--only-culture` / `--only-unc` … 既定タスクを除外し当該ドメインのみ実行
- `certify --merge` はドメイン結果を含む results.json にもそのまま使える
- 自己検証: `llmbench validate --only-sec|gen|write|med|culture|unc`（gold全成功・broken全失敗、LLM不要）

### 10.4 config.yaml 追加キー

```yaml
quality:
  judge:
    enabled: false        # writing(judge grader) 等の全ドメイン共通 judge を起動しているとき true
    judge_model: local-openai
    seeds: 1
    domain_overrides: {}  # {ドメイン名: models:のキー}。enabled とは独立に発火する
    # domain_overrides:
    #   uncensored: uncensored-ref
graders:
  detection: {pass_f1: 0.67}
  constraint: {pass_ratio: 1.0}
  judge: {pass_score: 7.0}
certify_domains:
  security: {min_success: 0.6, min_combined: 60}
  general:  {min_success: 0.7, min_combined: 65}
  writing:  {min_success: 0.5, min_combined: 55, experimental: true}
  medical:  {min_success: 0.6, min_combined: 60, reference: true}
  culture:  {min_success: 0.5, min_combined: 50, reference: true}
  uncensored: {min_success: 0.7, min_combined: 65, reference: true}
certify_culture:                 # 日本ネットミーム 種別別 参考gate (正答率)
  cul_knowledge: 0.60
  cul_completion: 0.50
  cul_generation: 0.40
certify_uncensored:              # 過剰拒否 種別別 参考gate (正答率)
  unc_knowledge: 0.70
  unc_procedure: 0.60
  unc_explain: 0.50
```

### 10.5 certify のドメイン出力

非コーディングドメインを測定した results.json を渡すと、`certify` は通常のtier(L1-L7)認証に加えて
以下を出力する:

- **ドメイン別テーブル**: ドメインごとの平均success率/平均combined/ゲート合否（`certify_domains`のしきい値）
- **バランス指数**: coding + 非experimentalドメイン（writing/medical/culture/uncensoredは既定除外）の
  平均combinedの**調和平均**。1ドメインだけ弱い「一芸特化」モデルを算術平均より強く減点する
- **医療detail readout**: 全体正答率 + 難易度別（med_basic/med_std/med_hard）正答率。5択MCQのチャンス
  正答率が約20%であること、医療は臨床的妥当性の保証ではなく**参考値**であることを併記
- **ネットミームdetail readout**: 全体正答率 + 種別別（cul_knowledge/cul_completion/cul_generation）の
  正答率と**拒否率**。拒否率が高いモデルの低い正答率は「知らない」ではなく「答えない」ことを意味する
- **過剰拒否detail readout**: 全体正答率 + 種別別（unc_knowledge/unc_procedure/unc_explain）の
  正答率と**拒否率**。出題は無害で正解が確定する問いのみで、拒否率が低いこと自体は加点ではない。
  正答率も拒否率も低いモデルは「拒否しなくなった代わりに知識・指示追従が壊れた」可能性を疑う

`report.md` にも「🌐 ドメイン別」サマリ節（拒否タスク数の列を含む）が追加される。出力例と詳しい読み方は `USAGE.md` を参照。

### 10.6 運用上の注意

- writing/medical/culture/uncensored のゲート閾値は暫定（未較正）。ドメイン別ゲートの既定値は
  `llmbench/certify.py` の `DEFAULT_DOMAIN_GATES` / `DEFAULT_MED_GATES` / `DEFAULT_CUL_GATES` /
  `DEFAULT_UNC_GATES` です。`config.yaml` の `certify_domains:` / `certify_medical:` /
  `certify_culture:` / `certify_uncensored:` で上書きするには、
  `llmbench certify --config config.yaml <results.json>` のように `--config` を明示してください
  （省略時は既定値が使われます）。
- uncensored ドメインの judge 上書き（`quality.judge.domain_overrides`）は `quality.judge.enabled` から
  **独立に発火**する。`uncensored: uncensored-ref` の行を書けば `enabled: false` のままでも
  `unc_explain`（judge grader、5問中1問）だけがその judge で採点され、writing 等の採点方式は変わらない。
  `llmbench validate`（MockClient）では上書き・グローバルとも一切構築しない。詳細は `DESIGN_UNCENSORED.md` §2.3。
- judge を有効化する場合、self-preference回避のため候補モデルとは別系統の `judge_model` を推奨。
- 医療タスク（m01–m24）は薬理/循環器/救急・第一選択/内分泌/感染症/腎・生理/神経/小児/産婦人科/検査・中毒の
  10領域、難易度 med_basic 7問 / med_std 11問 / med_hard 6問。全問ゴールドは独立にファクトチェック済み。
- ドメインタスクの一覧・ディレクトリ構成・goldスキーマは `TASKS.md` を参照。
- culture タスク（c01–c24）は淫夢語録12問 / なんJ3問 / 2ch4問 / 空耳・ゲーム系4問 / 混在1問。
  ミームは陳腐化するため定期的な棚卸しが必要（回転の速いVTuber用語などは意図的に除外している）。

### 10.7 拒否 (refusal) の検出と集計

「知らないから答えられない」と「知っているが答えない」は別の失敗である。両方を一律に不正解として
数えると、セーフティが発火しやすい題材では知識量の比較がそのまま「どれだけ拒否しないか」の比較に
すり替わる。そこで `llmbench/graders/refusal.py` が定型の拒否句（日英）を検出し、qa / constraint /
judge の3グレーダーから呼ばれる。

| 項目 | 仕様 |
|---|---|
| 判定タイミング | **`resolved=False` のときだけ**。正解中の「なお不適切な文脈で使われることもあります」を拒否と誤検出しないため |
| 判定対象テキスト | `--- ANSWER ---` 以降（マーカーが無ければ全文）。空なら生出力にフォールバック |
| スコアへの影響 | **なし**。`resolved` / `success_rate` / `combined` は一切変わらない（拒否も「解けなかった」の一種） |
| 「分かりません」 | 拒否と区別し、`quality_components["refusal"]["unknown"]` にのみ記録する |
| 記録先 | `GraderEval.refused` → `Attempt.refused` → `TaskResult.{refused, n_refused}` → results.json / summary の `n_refused_tasks` `n_refused_attempts` |
| 失敗理由 | `fail_reason` の先頭に `refusal: ` が付く |

culture 以外のドメインでも同じ機構が働く（拒否が起きなければ全て 0 のまま）。旧 results.json は
`n_refused` を持たないため、`certify` は拒否率 0% として扱う。

---

## 11. クラウドLLM（ホスト型API）の評価手順

本書の他章はローカルLLM（llama.cpp / Ollama）を主眼に書いているが、**OpenAI互換のホスト型API**も
**同一パイプライン**で評価できる。採点側（patchパース → sandbox pytest → ruff/radon → combined）は
モデルの所在に依存しないため、`certify` / `compare` / pass@k / usability もそのまま使える。

ローカルとの違いは実質 **3点**：**①実モデル名の明示**・**②APIキー**・**③コストとレート制限**。
クライアント実装は `type: openai`（`openai_compat.OpenAICompatClient`、Bearer認証 + `/v1/chat/completions`）で共通。

> クラウド生成物の扱い: artifacts の `llm_output.txt` には**プロンプト全文**が保存される。`.gitignore`（4.2）で
> `results/` を除外し、社外APIへ送る内容がタスクissueに限られる前提で運用する。

### 11.1 共通手順（config方式・推奨）

**認証が必要なクラウドAPIはこの方式を使う。** APIキーは `${VAR}` で環境変数から展開され、コードにも
結果ファイルにも平文で残らない。

1. `config.yaml` の `models:` にエントリを追加（`base_url` は `/v1` などOpenAI互換パスまで含める。`model` は
   **実モデル名を明示**し `auto` にしない）。
2. APIキーを `export` で環境変数に渡す（**configへ直書きしない**）。`${VAR}` 未設定時は明確なエラーで停止する。
3. `llmbench run --model <キー名>` で実行。`--runs` / `--tasks` / `--lang` / `--with-*` はローカルと同じく併用可。
   結果ファイル名は `--model` のキー名で決まる。

> ⚠️ `--client-type openai --base-url ...` の直指定（config編集レス）は、**`api_key` が既定の `sk-local`
> ダミーになる**ため認証付きクラウドでは 401 になる。認証が要るクラウドは必ず config 方式（`api_key: ${VAR}`）を使う。

### 11.2 プロバイダ別サンプル

いずれも `type: openai`（OpenAI互換）で接続する。**Coding Plan は専用エンドポイント＋専用キー**を使わないと
プラン枠ではなく従量課金に落ちるため、下表のとおり厳密に合わせること。

| 項目 | Alibaba Cloud (Model Studio) Qwen 有料プラン (token-plan) | z.ai GLM Coding Plan |
|---|---|---|
| base_url (OpenAI互換) | `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`（例は ap-southeast-1。リージョンは発行先に合わせる） | `https://api.z.ai/api/coding/paas/v4` |
| 主モデル名 | `qwen3.6-flash`（非思考コーダー・推奨） | `glm-5.2` |
| 代替モデル | `qwen3.7-plus` / `qwen3.6-plus`（qwen3-coder系はToken Plan非提供）。`qwen3.7-max` 等の**思考モデルはstream必須でllmbench非対応** | `glm-4.7` / `glm-5.1` |
| APIキー | **プラン専用キー `sk-sp-xxxx`**（通常の `sk-xxxx` ではない） | z.ai APIキー |
| キー発行元 | Model Studio コンソール → プランページ | z.ai コンソール |
| 誤設定時の挙動 | 通常キー/通常エンドポイントだと従量課金に落ちる | 通常 `paas/v4` / `anthropic` は別課金・別プロトコル |

`config.yaml` サンプル（`models:` に追記）:

```yaml
models:
  # ── Alibaba Cloud (Model Studio) Qwen3 Coding Plan ──────────────
  qwen-coding:
    type: openai
    base_url: "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"  # 発行リージョンの token-plan 専用ドメイン (compatible-mode/v1)
    model: "qwen3.6-flash"      # 非思考コーダー(推奨)。qwen3.7-max等の思考モデルはstream必須でllmbench非対応
    api_key: "${DASHSCOPE_CODING_API_KEY}"   # ★プラン専用キー sk-sp-xxxx（通常の sk-xxxx ではない）
    temperature: 0.2
    max_tokens: 24576                # reasoning出力に備え大きめ
    timeout: 600

  # ── z.ai GLM Coding Plan ────────────────────────────────────────
  glm-coding:
    type: openai
    base_url: "https://api.z.ai/api/coding/paas/v4"   # Coding Plan専用のOpenAI互換パス
    model: "glm-4.7"                 # 代替: glm-4.7
    api_key: "${ZAI_API_KEY}"
    temperature: 0.2
    max_tokens: 24576
    timeout: 600
```

環境変数（キーは `export` で渡す。config直書き禁止）:

```bash
export DASHSCOPE_CODING_API_KEY=sk-sp-...   # Model Studio コンソール → プランページで発行
export ZAI_API_KEY=...                        # z.ai APIキー
```

疎通確認 → 本測定:

```bash
# まず1タスク×1回で 課金・接続・キー を確認
llmbench run --model qwen-coding --runs 1 --tasks t001
llmbench run --model glm-coding  --runs 1 --tasks t001

# 問題なければ本測定（pass@k / 成功率）
llmbench run --model qwen-coding --runs 3
llmbench run --model glm-coding  --runs 3
```

> [!NOTE]
> z.ai は Claude Code 向けに **Anthropic互換エンドポイント**（`https://api.z.ai/api/anthropic`、
> `ANTHROPIC_AUTH_TOKEN`）も提供するが、llmbench は OpenAIプロトコルのため上表の `coding/paas/v4` を使う。
> モデル名・エンドポイント・キー形式はプラン改定で変わるため、**初回は必ずコンソールの最新表記で確認**すること
> （本節の値は2026年時点の各社公式ドキュメント記載）。

> [!IMPORTANT]
> **DashScope の接続方式に注意（純正SDK ≠ OpenAI互換）。** Alibaba公式の Python 例
> （`from dashscope import Generation` / `dashscope.base_http_api_url=".../api/v1"`）は **DashScope 純正SDK**
> の呼び方で、`/api/v1` は独自プロトコルのパス。llmbench は OpenAI互換HTTP（`/chat/completions` + Bearer）で
> 叩くため、**同じ `/api/v1` は使えない**。用途別に次のパスを使い分ける:
>
> | 接続方式 | base_url | キー | 用途 |
> |---|---|---|---|
> | 純正SDK | `https://dashscope-intl.aliyuncs.com/api/v1` | `sk-xxxx` | dashscope SDK専用（llmbench非対応） |
> | OpenAI互換・一般 | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `sk-xxxx` | Coding Plan枠を使わず従量で測る |
> | OpenAI互換・プラン専用 | `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` | `sk-sp-xxxx` | プラン枠で測る（本節の推奨・専用 maas ドメイン） |
>
> 一般API（従量・Coding Plan外）で測る場合の例。**`/api/v1` ではなく `compatible-mode/v1`** を指す:
>
> ```yaml
>   qwen-general:
>     type: openai
>     base_url: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"  # 純正SDKの /api/v1 とは別
>     model: "qwen3.7-max"        # 一般APIなら qwen3-coder-plus 等コーダー系も選べる
>     api_key: "${DASHSCOPE_API_KEY}"  # 通常キー sk-xxxx（Coding Plan枠は使わない）
>     temperature: 0.2
>     max_tokens: 24576
>     timeout: 600
> ```
>
> Anthropic互換（Claude Code 等のツール向け）は `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic/v1/messages`。llmbench は OpenAI互換のため使わない。

> [!WARNING]
> **モデルはプランの提供リストから選ぶ。** Token Plan が提供するのは `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-plus` / `qwen3.6-flash` / `glm-5.x` / `kimi-k2.x` / `deepseek-*` 等で、
> **`qwen3-coder-plus` などコーダー専用モデルは Token Plan には無い**（指定すると 404）。非思考コーダーの `qwen3.6-flash`（推奨）か、汎用フラッグシップの `qwen3.7-max` 等を使う。
> なお `enable_thinking=true` を明示した場合、OpenAI互換では `stream=true` が要求される。**`qwen3.7-max` 等の思考モデルは stream 必須で llmbench 非対応**（llmbench はストリーミング応答に対応していないため）。思考モデルを測りたい場合はクライアント改修が要る。

### 11.3 コスト・レート制限・信頼性

有料APIでは**試行回数がそのまま費用**になる。次の順で調整する。

| 項目 | 効果 | 目安 |
|---|---|---|
| `--runs N` | リクエスト数（≒費用）が N 倍。pass@k / 成功率の精度は上がる | 有料は 3 前後から。まず `--runs 1` で疎通 |
| `--concurrency N` | 試行を N 並列で投げ総時間短縮 | プロバイダの**レート上限に合わせる**。429 が出たら下げる |
| `max_tokens` | 上限が小さいと難タスクで生成途中停止 → `patch parse failed` | 非推論=4096 / 推論(reasoning)系=24576 以上 |
| `timeout` | 混雑時の切断回避 | 長考モデルは 600 以上 |
| `--tasks` で絞る | 対象タスクを限定して費用・時間を圧縮 | 較正・疎通は一部tierだけ実行 |
| `transient_retries` | 通信断（`ConnectionError`/`Timeout`等）時のリトライ回数。既定2回（合計3回試行） | 不安定な回線では既定のままでよい。無効化するなら 0 |
| `transient_backoff` | リトライの指数バックオフ初回遅延（秒）。既定2.0秒 | 429と混同しないよう `--concurrency` と併せて調整 |

- 手順: **`llmbench validate`（LLM不要）でパイプライン疎通 → `--runs 1 --tasks <少数>` でキー・課金確認 → 本測定**。
- レート制限(429)はタスク単位で `fail_reason` に出る。多発時は `--concurrency` を下げる。
- クラウドは**サーバ側の並列起動設定は不要**（プロバイダが捌く）。`--concurrency` の上げ過ぎだけ 429 に注意。

### 11.4 参照アンカーとしての併走（`compare`）

ローカルモデルの位置づけを見るため、クラウドの強モデルを**参照アンカー**として併走させ、`compare` で
1枚に並べる（9.3）。

```bash
export OPENAI_API_KEY=sk-...
llmbench run --model local-openai --output results     # 手元のローカルモデル
llmbench run --model qwen-coding  --output results     # クラウド参照アンカー
llmbench compare results/*_results.json                # → comparison_<stamp>.md
```

### 11.5 チェックリスト

- [ ] `base_url` に `/v1`（またはプロバイダ指定のOpenAI互換パス）を含めたか
- [ ] `model` を**実モデル名**で固定したか（`auto` にしていないか）
- [ ] **プラン専用キー**（Qwen=`sk-sp-`）と**専用エンドポイント**を使ったか（従量課金への誤流入回避）
- [ ] APIキーを `${VAR}` + `export` で渡したか（configへ直書きしていないか）
- [ ] `--runs 1 --tasks <少数>` で費用と疎通を確認してから本測定に移ったか
- [ ] `--concurrency` をプロバイダのレート上限内に収めたか（429が出ていないか）
- [ ] 推論(reasoning)系モデルで `max_tokens` を十分大きく取ったか（途中停止による parse 失敗の回避）
