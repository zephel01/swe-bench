# 📘 llmbench 利用ガイド

ローカルLLMを「機能正確性 × コード品質」で評価するための実践ガイドです。
インストールからモデル比較、**生成物（artifacts）を使った結果の読み解き方**までを、
今回の改善で追加された出力に沿って説明します。

> 概要・スコア定義・タスク追加は [README](README.md) を参照してください。
> 本ガイドは「実行して、結果をどう確認・分析するか」に焦点を当てます。

---

## 目次

1. [セットアップ](#1-セットアップ)
2. [まず自己検証する (`validate`)](#2-まず自己検証する-validate)
3. [モデルを設定する (`config.yaml`)](#3-モデルを設定する-configyaml)
4. [ベンチマーク実行 (`run`)](#4-ベンチマーク実行-run)
5. [出力の全体像](#5-出力の全体像)
6. [実行ログの読み方](#6-実行ログの読み方)
7. [レポート (`report.md`) の読み方](#7-レポート-reportmd-の読み方)
8. [生成物 (`artifacts/`) を使ったデバッグ](#8-生成物-artifacts-を使ったデバッグ)
9. [集計データ (`results.json`) の活用](#9-集計データ-resultsjson-の活用)
10. [典型的なワークフロー](#10-典型的なワークフロー)
11. [トラブルシューティング](#11-トラブルシューティング)

---

## 1. セットアップ

```bash
git clone https://github.com/zephel01/swe-bench.git
cd swe-bench
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

導入確認：

```bash
llmbench list-tasks      # 同梱タスク15個が一覧表示されればOK
```

---

## 2. まず自己検証する (`validate`)

LLMサーバを用意する前に、パイプライン自体が壊れていないかをモックで確認します。
LLM接続は不要です。

```bash
llmbench validate
```

- **mock-gold** … 正解コードを返すモック → 全タスク `RESOLVED` になるはず
- **mock-broken** … 壊れたコードを返すモック → 全タスク `FAILED`、combined平均が0になるはず

最後に `VALIDATION: PASS` が出れば、採点・パッチ適用・テスト隔離・スコア計算まで
すべて健全です。タスクを自作した直後の確認にも使えます。

```bash
llmbench validate --tasks t016        # 追加した特定タスクだけ検証
```

---

## 3. モデルを設定する (`config.yaml`)

接続は2系統。`config.yaml` の `base_url` / `model` を自分の環境に合わせて編集します。

```yaml
models:
  local-openai:                         # llama.cpp / LM Studio / vLLM など
    type: openai
    base_url: "http://localhost:8085/v1"
    model: "Qwopus3.6-27B-Coder-MTP"    # サーバ側のモデル名に一致させる
    api_key: "sk-local"                 # ローカルはダミーで可
    temperature: 0.2
    max_tokens: 4096
  local-ollama:
    type: ollama
    base_url: "http://localhost:11434"
    model: "qwen2.5-coder:32b"

run:
  issue_lang: en                        # ja に切替で language tax 検証
  test_timeout: 120

quality:
  llm_review:
    enabled: false                      # レビュー用モデル稼働時に true
    reviewer_model: local-openai
```

> 💡 **モデル比較のコツ**: 比較したいモデルごとに `models:` のエントリを増やし、
> `--model` を切り替えるだけ。`base_url` / `model` 以外の条件を揃えれば公平に比べられます。

---

## 4. ベンチマーク実行 (`run`)

```bash
# 全タスクを既定言語(en)で
llmbench run --model local-openai

# 特定タスクだけ・日本語issueで (language tax 計測)
llmbench run --model local-openai --tasks t001,t011 --lang ja

# 出力先を変える
llmbench run --model local-ollama --output results/ollama_run1
```

| オプション | 説明 |
|---|---|
| `--model` | **必須**。`config.yaml` の `models:` のキー名 |
| `--tasks` | カンマ区切りのタスクID（例: `t001,t003`）。省略で全タスク |
| `--lang` | `en` / `ja`。configの `issue_lang` を上書き |
| `--output` | 結果出力先ディレクトリ（既定: `results`） |
| `--tasks-dir` | タスク定義の場所（既定: `tasks`） |
| `--config` | 設定ファイル（既定: `config.yaml`） |

実行が終わると、標準出力に Resolved率・品質平均・Combined平均と、
保存された結果ファイルのパスが表示されます。

---

## 5. 出力の全体像

1回の `run` で、出力先（既定 `results/`）に **3種類** が生成されます。
ファイル名の `<stamp>` は実行時刻、`<model>` はモデル名です。

```
results/
├── <stamp>_<model>_results.json      # ① 集計・スコア (機械可読・軽量)
├── <stamp>_<model>_report.md         # ② 人が読むレポート
└── <stamp>_<model>_artifacts/        # ③ 生成物そのもの (★今回の改善の主役)
    └── <task_id>/
        ├── llm_output.txt            #   LLMの生出力 (パース失敗の原因確認)
        ├── generated/<path>          #   実際に適用された生成コード (動作確認)
        └── test_output.txt           #   pytest出力 (テスト失敗の原因確認)
```

役割分担：

| 出力 | いつ見るか |
|---|---|
| **実行ログ**（標準出力） | 実行中にその場で「動いてるか」を把握する |
| **`report.md`** ② | 実行後にスコアと品質を俯瞰する |
| **`artifacts/`** ③ | 失敗や低スコアの**原因をコードレベルで深掘り**する |
| **`results.json`** ① | スクリプトで集計・モデル間比較する |

---

## 6. 実行ログの読み方

改善後は、タスクごとに「**何が生成され、どう判定されたか**」がその場で分かります。

```
[3/15] t003 (easy) リスト要素の重複除去
    生成OK  files=[dedup.py]  214tok @ 126.9tok/s
      └ dedup.py (12 LOC): def dedup(items): ⏎ seen = set()
    ✅ RESOLVED  quality=100 combined=100  (1.5s)
```

各行の意味：

- **1行目** `[i/N] task_id (難易度) タイトル` — 進捗
- **2行目** `生成OK / 生成パース失敗` — LLM出力のパース結果。生成ファイル名・トークン数・tok/s
  - パース失敗時は `出力プレビュー:` にLLM生出力の冒頭が出る
- **3行目** `└ path (n LOC): コード冒頭` — 適用されたコードの行数と先頭2行プレビュー（目視確認用）
- **4行目** `✅ RESOLVED / ❌ FAILED` — テスト判定・quality・combined・生成時間
  - 失敗時は `| ...` で **pytest出力の末尾3行** が表示され、その場で失敗理由が分かる

失敗例：

```
[11/15] t011 (hard) ...
    生成OK  files=[parser.py]  402tok @ 98.0tok/s
      └ parser.py (35 LOC): def parse(s): ⏎ tokens = []
    ❌ FAILED (tests_failed)  quality=0 combined=0  (3.8s)
      | E       assert parse("1+2") == 3
      | E       AssertionError
      | 1 failed in 0.04s
```

---

## 7. レポート (`report.md`) の読み方

改善後のレポートは **サマリ → タスク別結果 → 難易度別 → タスク別詳細** の構成です。

### サマリ

```markdown
# llmbench レポート: local-openai

Issue言語: `en` / タスク数: 15

## サマリ

| 指標 | 値 |
|---|---|
| ✅ Resolved率 | **100.0%** (15/15) |
| 🏅 品質平均 (resolvedのみ) | **88.6 / 100** |
| 🎯 Combined平均 | **94.3 / 100** |

> 📂 生成物 ... は `<stamp>_<model>_artifacts/<task_id>/` に保存。
```

### タスク別結果（一覧表）

`Resolved` 列はアイコン（✅/❌）になり、**生成ファイル**列と**備考**列（失敗理由・パースエラー）が追加。
一覧で「どのタスクがどのファイルを生成し、なぜ落ちたか」まで掴めます。

| | Task | 難易度 | 生成ファイル | Quality | Combined | 生成時間 | tok/s | 備考 |
|---|---|---|---|---|---|---|---|---|
| ✅ | t003 | easy | `dedup.py` | 100 | 100 | 1.5s | 126.9 | — |
| ❌ | t011 | hard | `parser.py` | 0 | 0 | 3.8s | 98.0 | tests_failed |

### タスク別詳細

タスクごとに、難易度・判定・生成ファイル・生成物パス・**品質内訳（整形済み）**を表示。
旧版は生のdictでしたが、改善後は人が読める形式になりました：

```markdown
### ✅ t010 — CSV行のパース

- 難易度: medium / 判定: RESOLVED
- 生成ファイル: csv_line.py
- 生成物: `20260614_004946_local-openai_artifacts/t010/`
- ruff: ✅ 指摘なし (49 LOC)
- complexity: MI=67 / 最悪CCランク=B  score=62  (最複雑: csv_line.py:parse_csv_line (CC=8))
```

- **ruff**: 指摘件数・密度・違反ルール・スコア（指摘ゼロなら `✅ 指摘なし`）
- **complexity**: Maintainability Index・最悪CCランク・最も複雑な関数

---

## 8. 生成物 (`artifacts/`) を使ったデバッグ

改善の主役。**「なぜ落ちたか」「なぜ品質が低いか」をコードレベルで追える**ようになりました。

```
<stamp>_<model>_artifacts/<task_id>/
├── llm_output.txt      # LLMが返した生テキスト全体
├── generated/<path>    # パースして実際に適用したコード
└── test_output.txt     # そのコードに対するpytestの全出力
```

### ケース別の使い分け

| 症状 | 見るファイル | 分かること |
|---|---|---|
| **パース失敗**（`生成パース失敗`） | `llm_output.txt` | `--- FILE: path ---` マーカーやコードブロックの形式崩れ |
| **テスト失敗**（`tests_failed`） | `test_output.txt` → `generated/` | どのassertで落ちたか → 該当コードのロジック誤り |
| **品質が低い** | `generated/<path>` | ruff指摘箇所・複雑な関数を実コードで確認 |
| **動いてるか半信半疑** | `generated/<path>` | 生成コードをそのまま読んで妥当性を判断 |

> 💡 `generated/` 配下は適用された**そのままのコード**です。手元にコピーして
> 自分のpytestやエディタで再現確認することもできます。

---

## 9. 集計データ (`results.json`) の活用

スコアと集計に特化した軽量JSON（生出力やテストログなどの大きいフィールドは
artifactsに分離されているため軽い）。モデル間比較やCIに向きます。

```jsonc
{
  "model": "local-openai",
  "issue_lang": "en",
  "artifacts_dir": "20260614_004946_local-openai_artifacts",
  "summary": {
    "resolved_rate": 1.0,
    "avg_quality_resolved": 88.6,
    "avg_combined": 94.3,
    "n_tasks": 15
  },
  "results": [ /* タスクごとのスコア・品質内訳 */ ]
}
```

### モデル比較の例

```bash
# 複数モデルを同条件で実行
llmbench run --model local-openai --output results
llmbench run --model local-ollama --output results

# combined平均をまとめて比較
for f in results/*_results.json; do
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); \
    print(f\"{d['model']:20s} resolved={d['summary']['resolved_rate']*100:5.1f}%  \
combined={d['summary']['avg_combined']:.1f}\")" "$f"
done
```

---

## 10. 典型的なワークフロー

### A. 新しいモデルを初めて評価する

```bash
llmbench validate                              # 1. パイプライン健全性
# 2. config.yaml にモデル追加
llmbench run --model <model> --tasks t001      # 3. 1タスクで疎通確認
llmbench run --model <model>                   # 4. 全タスク本番
# 5. report.md でスコア俯瞰 → artifacts/ で失敗を深掘り
```

### B. language tax（日本語指示による性能低下）を測る

```bash
llmbench run --model <model> --lang en --output results/en
llmbench run --model <model> --lang ja --output results/ja
# 両者の resolved_rate / avg_combined を比較
```

### C. 失敗タスクを集中的に調べる

```bash
# report.md で ❌ のタスクIDを特定し、そのタスクだけ再実行
llmbench run --model <model> --tasks t011,t013
# artifacts/t011/test_output.txt と generated/ で原因を確認
```

---

## 11. トラブルシューティング

| 症状 | 原因・対処 |
|---|---|
| `config not found` | `--config` のパス、または実行ディレクトリを確認 |
| 接続エラー / タイムアウト | `base_url` とサーバ稼働状況。`type` が `openai`/`ollama` と一致しているか |
| `model` 不一致エラー | `config.yaml` の `model` をサーバ側の実モデル名に合わせる |
| 全タスクが `生成パース失敗` | モデルが `--- FILE: path ---` + コードブロック形式に従えていない。`llm_output.txt` を確認し、必要なら `max_tokens` を増やす（出力途中切れ） |
| `tests_failed` が多い | `artifacts/<id>/test_output.txt` で失敗assertを確認。ロジック誤りかパッチ対象ファイル違い |
| `validate` が FAIL | パイプライン側の問題。タスク自作直後ならディレクトリ構成（`gold/` `tests/`）を確認 |
| 品質スコアが安定しない | `temperature` を下げる（既定0.2推奨）。LLMレビューを使う場合は `reviewer_model` の稼働を確認 |

---

> 改善点まとめ: **①生成物の永続保存**（llm_output / generated / test_output）、
> **②レポートの整形**（サマリ表・タスク別詳細・読める品質内訳）、
> **③実行ログの強化**（生成ファイル・コード冒頭・テスト失敗末尾）。
> これにより「スコアが出る」だけでなく「**なぜそのスコアなのかをコードまで遡って確認できる**」ようになりました。
