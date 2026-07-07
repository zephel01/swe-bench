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
3. [モデルを設定する (`config.yaml` / `model: auto`)](#3-モデルを設定する-configyaml--model-auto)
4. [モデルを選ぶ (`models` / Ollama動的選択)](#4-モデルを選ぶ-models--ollama動的選択)
5. [ベンチマーク実行 (`run`)](#5-ベンチマーク実行-run)
6. [信頼性を測る (`--runs` / pass@k)](#6-信頼性を測る---runs--passk)
7. [usability判定の読み方](#7-usability判定の読み方)
8. [モデルを横断比較する (`compare`)](#8-モデルを横断比較する-compare)
9. [出力の全体像](#9-出力の全体像)
10. [実行ログの読み方](#10-実行ログの読み方)
11. [レポート (`report.md`) の読み方](#11-レポート-reportmd-の読み方)
12. [生成物 (`artifacts/`) を使ったデバッグ](#12-生成物-artifacts-を使ったデバッグ)
13. [集計データ (`results.json`) の活用](#13-集計データ-resultsjson-の活用)
14. [典型的なワークフロー](#14-典型的なワークフロー)
15. [トラブルシューティング](#15-トラブルシューティング)

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
llmbench list-tasks            # 既定40個が一覧表示されればOK
llmbench list-tasks --with-l6  # L6 architect 20個を加えて計60個
llmbench list-tasks --with-l7             # L7 grandmaster 40個を加えて計80個
llmbench list-tasks --with-l6 --with-l7   # L6+L7 両方で計100個
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

## 3. モデルを設定する (`config.yaml` / `model: auto`)

`config.yaml` の `base_url` を自分の環境に合わせるだけ。**`model` は `auto` 推奨**です。

```yaml
models:
  local-openai:                         # llama.cpp / LM Studio / vLLM など
    type: openai
    base_url: "http://localhost:8085/v1"
    model: "auto"                       # サーバのロード中モデルを自動採用 (config編集不要)
    api_key: "sk-local"                 # ローカルはダミーで可
    temperature: 0.2
    max_tokens: 4096
  local-ollama:
    type: ollama
    base_url: "http://localhost:11434"
    model: "qwen2.5-coder:32b"
  ref-gpt:                              # compareの参照アンカー (API)
    type: openai
    base_url: "https://api.openai.com/v1"
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"        # ${VAR} は環境変数から展開

run:
  issue_lang: en                        # ja に切替で language tax 検証
  test_timeout: 120
  runs: 1                               # 既定の試行回数 (>1 で pass@k)
  sample_temp: 0.8                      # 複数試行時の温度

usability:                              # ティア分類のしきい値
  autonomous: {min_success: 0.9, min_quality: 80}
  assisted:   {min_success: 0.6, min_quality: 0}
```

> 💡 **`model: auto` が効くと config を二度と触らなくて済みます。** llama.cpp等でggufを
> 差し替える → そのまま `llmbench run` するだけ。llmbench が `/v1/models` から実モデル名を
> 取得し、レポート/結果ファイルもその実名でラベルします（`.gguf` は自動除去）。
> APIキーは `${OPENAI_API_KEY}` のように環境変数で渡せます（configに直書き不要）。

---

## 4. モデルを選ぶ (`models` / Ollama動的選択)

どんなモデルが使えるかは `models` で一覧できます（config定義 + Ollama稼働モデル）。

```bash
llmbench models
#   === config.yaml 定義モデル ===
#     local-openai (type=openai, model=auto)
#     local-ollama (type=ollama, model=qwen2.5-coder:32b)
#   === Ollama 稼働モデル (http://localhost:11434) ===
#     qwen2.5-coder:7b
#     llama3:8b
#     → config未定義でも `--model <名前>` でそのまま実行できます
```

- **Ollamaはconfig未定義でも直接指定可**: `llmbench run --model qwen2.5-coder:7b`。
  起動中のOllamaの `/api/tags` から自動解決します（接続先は `--ollama-host`）。
- Ollama未起動でも `models` はエラーにならず案内を出します。

---

## 5. ベンチマーク実行 (`run`)

```bash
# 全40タスクを既定言語(en)で1回
llmbench run --model local-openai

# 各タスク5回 → 成功率・pass@k・usability判定
llmbench run --model local-openai --runs 5

# 特定タスクだけ・日本語issueで (language tax 計測)
llmbench run --model local-openai --tasks t001,t011 --lang ja

# Ollamaの実モデル名を直接 / 出力先を変える
llmbench run --model qwen2.5-coder:7b --runs 5 --output results/qwen7b

# 接続先をCLIで直接指定 (config編集不要)
llmbench run --model auto --client-type openai --base-url http://localhost:8085/v1   # llama.cpp直結
llmbench run --model router --client-type multiagent --base-url http://localhost:8088 # CodeRouter
llmbench run --model qwen2.5-coder:32b --base-url http://192.168.1.10:11434           # リモートOllama
```

| オプション | 説明 |
|---|---|
| `--model` | **必須**。config の `models:` キー、または Ollama稼働モデル名 |
| `--runs` | 各タスクの試行回数。`>1` で成功率・pass@k を計測（既定: `run.runs` または1） |
| `--sample-temp` | 複数試行時のサンプリング温度（既定: `run.sample_temp` または0.8） |
| `--label` | 結果ラベルを明示指定（既定: `model:auto`時はサーバ検出名） |
| `--tasks` | カンマ区切りのタスクID（例: `t001,t003`）。省略で全タスク |
| `--lang` | `en` / `ja`。configの `issue_lang` を上書き |
| `--ollama-host` | Ollama接続先（未定義モデルの自動解決に使用） |
| `--base-url` | 接続先URLを明示指定。configの `base_url` を上書き(例: `http://localhost:8085/v1`) |
| `--client-type` | `openai` / `ollama` / `multiagent`。config未定義でも接続種別を直接指定(`--base-url` と併用) |
| `--output` | 結果出力先ディレクトリ（既定: `results`） |
| `--tasks-dir` / `--config` | タスク定義 / 設定ファイルの場所 |

実行が終わると、標準出力に Resolved率・（多試行なら）平均成功率・品質平均・Combined平均と、
保存された結果ファイルのパスが表示されます。

---

## 6. 信頼性を測る (`--runs` / pass@k)

1回成功しただけでは「使える」とは言えません。`--runs N` で各タスクをN回試行し、
**成功率(pass@1)** を主指標に信頼性を測ります。

```bash
llmbench run --model local-openai --runs 5
```

レポート/結果に出る信頼性指標：

| 指標 | 意味 |
|---|---|
| **成功率 (pass@1)** | 1回試行で通る期待値。**信頼性の主指標** |
| ≥1成功 | N回中1回でも通ったか（再試行込みの到達可能性） |
| flaky | `2/5 passed` のように成功・失敗が割れる状態。不安定の証拠 |

`combined` は成功率でスケールされるため、フレるタスクは自動的に減点されます
（例: 60%成功・品質90 → 0.6×95 = 57点）。同じモデルでも `--runs` を増やすと、
1サンプルでは見えなかった**フレが顕在化**します。

---

## 7. usability判定の読み方

各タスクは success_rate と quality から3ティアに分類されます（しきい値は `config.yaml`）。

| ティア | 既定条件 | 運用判断 |
|---|---|---|
| 🟢 自律 | success ≥ 0.9 かつ quality ≥ 80 | レビューほぼ不要で任せられる |
| 🟡 補助 | success ≥ 0.6 | レビュー前提なら使える |
| 🔴 不可 | 上記未満 | この種のタスクには任せられない |

レポートの「usability判定」セクションには、ティア集計・**難易度×ティアの割合**・
保守的な総合推奨（🔴不可が1つでもあれば「自律」と言い切らない）が出ます。
「品質軸で🟡補助」（毎回成功するが quality<80）と「信頼性軸で🟡補助/🔴不可」（フレる）の
両方を見分けられます。

---

## 8. モデルを横断比較する (`compare`)

複数の `results.json` を1枚のレポートにまとめます。

```bash
# 自分のモデルと参照モデル(API)を同条件で
llmbench run --model local-openai --runs 5 --output results
OPENAI_API_KEY=sk-... llmbench run --model ref-gpt --runs 5 --output results

# 横断比較レポートを生成
llmbench compare results/*_results.json --output results
```

出力 `comparison_<stamp>.md` には、Combined降順のランキング（最良比の**相対スコア**）、
usabilityティア比較、**タスク別Combinedマトリクス**（行内ベストを太字）が並びます。
参照モデルを併置すると、ローカルモデルのスコアが「どの位置か」を解釈できます。

---

## 8.5 使えるラインを判定する (`certify`)

`compare` がモデル**間**の相対比較なのに対し、`certify` は1モデルの **絶対的な到達度**を
tier合格制で出します。難易度を tier(L1-L7) にマップし、tierごとの平均成功率/combinedが
gate を満たすかを**独立に**評価します。

```bash
llmbench certify results/<stamp>_<model>_results.json
```

主判定は **使えるライン = L4(expert) を独立に合格**（成功率 ≥ 60% かつ combined ≥ 55）。
参考として累積到達レベル（下位tierから連続合格した最上位）と、独立合格tier一覧も表示します。

| Gate | 条件 (tier平均) | 意味 |
|---|---|---|
| L1 / L2 | 成功率 ≥ 90% / ≥ 85% | 基本〜単純作業 |
| L3 hard | 成功率 ≥ 75% かつ combined ≥ 60 | 実務の単純〜中級バグ |
| **L4 expert** | **成功率 ≥ 60% かつ combined ≥ 55** | **✅ 使えるライン** |
| L5 frontier | 成功率 ≥ 40% | フロンティア級 |
| L6 architect | 成功率 ≥ 55% かつ combined ≥ 60 (暫定) | アーキテクト級 (上位帯の分離) |
| L7 grandmaster | 成功率 ≥ 35% かつ combined ≥ 55 (暫定・天井評価用) | グランドマスター級 (天井評価帯) |

> 閾値は `llmbench/certify.py` の `DEFAULT_GATES` で調整可能。実モデル較正で確定するのが推奨。
> `--runs 5` 程度で実行した results を渡すと、成功率(pass@1平均)が安定します。
> L6 は `--with-l6` で測定した results にのみ現れます（既定の40問評価では未測定扱い）。
> L7 は `--with-l7` で測定した results にのみ現れます（既定の40問評価では未測定扱い）。
> L7 のgateは暫定値であり、実モデル較正で確定する（天井評価帯 — 現行タスク群では頭打ちが見えない水準）。

### L6 (architect) の追加20問を含めて実行する

L6 は既定では読まれません。`--with-l6` で別台帳 `tasks/tasks_l6.jsonl` をマージし、
40 + 20 = 60問で評価します（`--l6-ledger` で台帳名を変更可）。

```bash
llmbench run --model local-openai --runs 5 --with-l6        # 計60問
llmbench run --model local-openai --with-l6 \
  --tasks t041,t042,t043,t044,t045,t046,t047,t048,t049,t050,\
t051,t052,t053,t054,t055,t056,t057,t058,t059,t060            # L6だけ
```

### L7 (grandmaster) の追加40問を含めて実行する

L7 も既定では読まれません。`--with-l7` で別台帳 `tasks/tasks_l7.jsonl` をマージし、
40 + 40 = 80問で評価します（`--l7-ledger` で台帳名を変更可）。`--with-l6` と併用すると
40 + 20 + 40 = 100問になります。

```bash
llmbench run --model local-openai --runs 5 --with-l7            # 計80問
llmbench run --model local-openai --with-l6 --with-l7 --runs 5  # 計100問 (L6+L7)
```

L7 (grandmaster) は天井評価帯 — **数値安定性**(t061-068)・**状態一貫性**(t069-076)・
**複数結合バグ**(t077-084)・**深い並行性**(t085-092)・**敵対的パース・セキュリティ**(t093-100)
の5軸×8問で構成されます。`t098`（ReDoS検知）のみ `perf_timeout: 30` が個別設定されています。

### 試行の並列実行（`--concurrency`）

`--runs N` の各試行は既定では直列実行です。タスク数が多いと時間がかかるため、
`--concurrency K` で試行を同時実行して総処理時間を短縮できます。

**前提**: llama.cpp サーバを `--parallel K -cb` で起動しておくこと。
サーバ側の `--parallel` とベンチ側の `--concurrency` は**同じ値に揃えます**。

```bash
# 並列計測: サーバ --parallel 5 で起動 → 試行を5並列
llmbench run --model local-openai --runs 5 --concurrency 5
llmbench run --model local-openai --with-l6 --runs 5 --concurrency 5   # 60タスク
llmbench run --model local-openai --with-l6 --with-l7 --runs 5 --concurrency 5   # 100タスク

# 単発計測: サーバ --parallel 1 で起動 → 直列
llmbench run --model local-openai --runs 5 --concurrency 1
```

**トレードオフ**:

- ✅ 総終了時間は短縮（実測で約2.2倍速）。大量タスクの消化向き
- ⚠️ 1ストリームあたりの tok/s は低下（実測 264→110 tok/s）。GPUを試行間で取り合うため
- → **モデル単体の速度(tok/s)を正確に測るなら `--concurrency 1`**、量をこなすなら並列、と目的で使い分ける
- 正答率・品質スコアは並列度の影響をほぼ受けません

> 既定値は `config.yaml` の `run.concurrency`、または `--concurrency` で都度上書き。
> 実際の並列数は `runs` を超えません（`min(concurrency, runs)`）。MockClient は常に直列です。

---

## 9. 出力の全体像

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

## 10. 実行ログの読み方

改善後は、タスクごとに「**何が生成され、どう判定されたか**」がその場で分かります。

```
[3/20] t003 (easy) リスト要素の重複除去
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
[11/20] t011 (hard) ...
    生成OK  files=[parser.py]  402tok @ 98.0tok/s
      └ parser.py (35 LOC): def parse(s): ⏎ tokens = []
    ❌ FAILED (tests_failed)  quality=0 combined=0  (3.8s)
      | E       assert parse("1+2") == 3
      | E       AssertionError
      | 1 failed in 0.04s
```

---

## 11. レポート (`report.md`) の読み方

レポートは **サマリ → usability判定 → タスク別結果 → 難易度別 → タスク別詳細** の構成です。

### サマリ

`--runs N` を付けると、成功率(pass@1)・≥1成功・usability判定が加わります。

```markdown
# llmbench レポート: Qwopus3.6-27B-Coder-MTP-Q6_K
Issue言語: `en` / タスク数: 20 / 試行: ×5

## サマリ
| 指標 | 値 |
|---|---|
| ✅ Resolved率 | **95.0%** (19/20) |
| 🎲 平均成功率 (pass@1, ×5) | **93.0%** |
| 🔁 ≥1成功できたタスク | **95.0%** (19/20) |
| 🏅 品質平均 (resolvedのみ) | **89.8 / 100** |
| 🎯 Combined平均 | **88.2 / 100** |

## 🧭 usability判定
- 🟢 自律 17/20 / 🟡 補助 2/20 / 🔴 不可 1/20
> 総合推奨: おおむね自律。ただし🔴不可 1/20 (5%) は要注意
```

### タスク別結果（一覧表）

`判定` 列に usability ティア（🟢/🟡/🔴）が出ます。多試行時はさらに **信頼性**列
（`4/5 (成功率80%)`）が加わり、`備考` に `flaky 3/5 passed` 等が入ります。

| | Task | 難易度 | 判定 | 信頼性 | 生成ファイル | Quality | Combined | 備考 |
|---|---|---|---|---|---|---|---|---|
| ✅ | t007 | medium | 🟡 補助 | 4/5 (成功率80%) | `word_freq.py` | 100 | 80 | flaky 4/5 passed |
| ❌ | t020 | hard | 🔴 不可 | 0/5 (成功率0%) | `calc.py` | 0 | 0 | tests failed |

### タスク別詳細

タスクごとに、難易度・判定・**信頼性(pass@1)**・usabilityティア・生成物パス・品質内訳を表示。

```markdown
### ✅ t007 — word_frequencies treats Word/word as different
- 難易度: medium / 判定: RESOLVED (flaky 4/5 passed) / usability: 🟡 補助
- 信頼性: 成功 4/5 （成功率 80% = pass@1） / 5回中≥1成功: ✓
- 生成ファイル: word_freq.py
- 生成物: `<stamp>_<model>_artifacts/t007/`
- 品質内訳（下記は代表1試行の値。上のQuality は5試行の平均）:
  - ruff: ✅ 指摘なし (17 LOC)
  - complexity: MI=100 / 最大複雑度ランク=A → score=100
```

> ⚠️ **多試行時の注意**: 品質内訳（ruff/complexity）は**代表1試行**の値、Quality数値は
> **N試行の平均**です。一致しないことがあるのは仕様（注記つきで表示されます）。

---

## 12. 生成物 (`artifacts/`) を使ったデバッグ

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

## 13. 集計データ (`results.json`) の活用

スコアと集計に特化した軽量JSON（生出力やテストログなどの大きいフィールドは
artifactsに分離されているため軽い）。モデル間比較やCIに向きます。

```jsonc
{
  "model": "Qwopus3.6-27B-Coder-MTP-Q6_K",   // model:auto検出時は実モデル名
  "issue_lang": "en",
  "artifacts_dir": "<stamp>_<model>_artifacts",
  "summary": {
    "resolved_rate": 0.95,
    "avg_quality_resolved": 89.8,
    "avg_combined": 88.2,
    "n_tasks": 20,
    "runs": 5,
    "usability": { "autonomous": 17, "assisted": 2, "unusable": 1 },
    "avg_success_rate": 0.93,   // = 平均pass@1 (多試行時のみ)
    "solved_any_rate": 0.95,    // N回中≥1成功 (多試行時のみ)
    "avg_pass_at_k": 0.95       // k=runs時は退化する点に注意
  },
  "results": [
    {
      "task_id": "t007", "difficulty": "medium", "title": "...",
      "resolved": true, "quality_score": 100.0, "combined": 80.0,
      "runs": 5, "n_pass": 4, "success_rate": 0.8,
      "pass_at_1": 0.8, "pass_at_k": 1.0,
      "usability_tier": "assisted",
      "parse_ok": true, "fail_reason": "flaky 4/5 passed",
      "attempts": [ /* 各試行の {resolved, quality, combined} */ ],
      "quality_components": { /* ruff / complexity */ }
    }
  ]
}
```

> 注: `raw_output` / `parsed_files` / `test_output` は results.json には含まれず、
> `artifacts/<task_id>/` 側に保存されます（JSONを軽量に保つため）。

### `compare` でまとめて比較（推奨）

```bash
llmbench run --model local-openai --runs 5 --output results
llmbench run --model ref-gpt      --runs 5 --output results
llmbench compare results/*_results.json --output results   # ランキング＋マトリクス
```

### jq で手早く確認

```bash
# 失敗・フレたタスクを抽出
jq -r '.results[] | select(.success_rate < 1) | "\(.task_id)\t\(.success_rate)\t\(.fail_reason)"' \
  results/<stamp>_<model>_results.json
```

---

## 14. 典型的なワークフロー

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

## 15. トラブルシューティング

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
