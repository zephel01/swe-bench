# 🛠️ llmbench 運用マニュアル（artifacts / 信頼性 / usability / 比較 / モデル解決）

本書は、artifacts保存・レポート刷新に加え、その後追加された **信頼性(pass@k)・usability判定・
モデル横断比較・モデル解決(model:auto/Ollama動的)** までを、「運用・保守・他システム連携」の
観点でまとめた**運用＆リファレンスマニュアル**です。

ドキュメントの役割分担：

| ドキュメント | 対象読者 | 内容 |
|---|---|---|
| [README.md](README.md) | はじめての人 | 概要・特徴・スコア定義・タスク追加 |
| [USAGE.md](USAGE.md) | 利用者 | 実行手順と結果の**読み解き方** |
| [CHANGES.md](CHANGES.md) | 全員 | 追加機能の要約と変更履歴 |
| **本書（運用マニュアル）** | 運用・保守・連携担当 | 出力ファイルの**仕様**・内部実装・運用上の注意・移行・自動化 |

> 対象バージョン: 全20タスク・多試行(pass@k)・usability・compare・`model:auto` 対応版。
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
| ⑧ | **難タスク t016–t020** | 失敗が出る実務的タスクで識別力を確保（全20タスク） |

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
| `avg_success_rate` | 平均成功率（=平均pass@1）。**多試行時のみ** |
| `solved_any_rate` | N回中≥1成功したタスクの割合。**多試行時のみ** |
| `avg_pass_at_k` | 平均pass@k。**多試行時のみ**（k=runsで退化する点に注意） |

`results[]`（**軽量化済み** — 大きいフィールドは除外）：

| キー | 型 | 説明 |
|---|---|---|
| `task_id` | str | 例: `t001` |
| `difficulty` | str | `easy` / `medium` / `hard` |
| `title` | str | タスクタイトル |
| `resolved` | bool | テスト合格判定（多試行では success_rate≥0.5） |
| `quality_score` | float | 0–100。多試行では**成功試行の平均** |
| `combined` | float | 0–100。`success_rate × (floor + (1-floor)×quality/100) × 100` |
| `latency_sec` / `tokens_per_sec` / `completion_tokens` | — | 速度メトリクス（多試行は平均） |
| `fail_reason` | str | 失敗理由。部分成功は `flaky c/N passed` |
| `parse_ok` / `parse_error` | bool/str | 代表試行のパース成否・理由 |
| `runs` / `n_pass` | int | 試行回数 / 成功回数 |
| `success_rate` / `pass_at_1` / `pass_at_k` | float | 成功率（=pass@1）/ pass@k |
| `attempts` | array | 各試行の `{resolved, quality, combined, fail_reason}` |
| `usability_tier` | str | `autonomous` / `assisted` / `unusable` |
| `quality_components` | obj | 代表試行の ruff / complexity / … 内訳 |

> ⚠️ **`results.json` に含まれないフィールド**（artifactsへ分離）:
> `raw_output`（LLM生出力）・`parsed_files`（生成コード）・`test_output`（pytest出力）。
> これらは `ARTIFACT_FIELDS` として `save_run()` の `_lean()` で除外されます。
> `changed_files` はプロパティのためJSONには出力されません（artifacts側の `generated/` で確認）。

### 2.2 `report.md` の構成

刷新後の構成は **サマリ → タスク別結果 → 難易度別 → タスク別詳細**。

- **サマリ**: Resolved率（n/N）・品質平均・Combined平均を表形式。`artifacts_dir` がある場合は保存先を注記。
- **タスク別結果（一覧表）**: 先頭列が ✅/❌ アイコン、**生成ファイル**列と**備考**列（失敗理由・パースエラー）を追加。
- **難易度別**: easy/medium/hard ごとの resolved 数と品質平均。
- **タスク別詳細**: タスクごとに難易度・判定・生成ファイル・生成物パス・**整形済み品質内訳**（ruff/complexityを日本語で説明）。

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
[3/15] t003 (easy) リスト要素の重複除去
    生成OK  files=[dedup.py]  214tok @ 126.9tok/s
      └ dedup.py (12 LOC): def dedup(items): ⏎ seen = set()
    ✅ RESOLVED  quality=100 combined=100  (1.5s)
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
  - 新: `| | Task | 難易度 | 生成ファイル | Quality | Combined | 生成時間 | tok/s | 備考 |`（9列、先頭=✅/❌アイコン）
  - Resolved の `O/X` は ✅/❌ に変更。Markdownテーブルを機械パースしている場合は要修正。
- セクション見出し `## 品質内訳 (タスク別)` は `## タスク別詳細` に変更。

### 7.3 `config.yaml`

- サンプルの `local-openai` が `base_url: http://localhost:8085/v1` / `model: Qwopus3.6-27B-Coder-MTP` に更新。
  これは設定例の変更であり挙動には影響しません。**結果ファイル名は `--model` のキー名**（`local-openai`）で決まるため、
  キー名を変えない限りファイル名は安定します。

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
| `llmbench/cli.py` | `models` / `compare` サブコマンド・`--runs`/`--sample-temp`/`--label`/`--ollama-host` |
| `config.yaml` | `model:auto`・`run.runs`/`sample_temp`/`ollama_host`・`usability:`・`ref-gpt` |
| `tasks/` | 難タスク t016–t020 追加（全20タスク） |

> 検証状況: `llmbench validate` PASS（gold 20/20・broken 20/20）、多試行集計・usability・compare・
> モデル解決の各単体、ruff（追加/変更ファイル指摘ゼロ）、`compileall` を確認済み。

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
- 接続先優先順: `--ollama-host` > config の ollama モデル `base_url` > `http://localhost:11434`。
- `--label` で明示固定。APIキーは `${VAR}` を環境変数展開。

### 9.5 運用上の注意

- **多試行はディスク/時間が N 倍**。artifactsは代表1試行のみ保存するので肥大化は限定的だが、生出力は残る。
- pass@k の解釈は 9.1 の通り。`avg_pass_at_k` を「汎化性能」と誤読しないこと。
- レポート表の列数が増えている（判定・信頼性列）。機械パースは要追従（7章の移行メモ参照）。
