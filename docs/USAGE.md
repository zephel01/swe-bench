# 📘 llmbench 利用ガイド

ローカルLLMを「機能正確性 × コード品質」で評価するための実践ガイドです。
インストールからモデル比較、**生成物（artifacts）を使った結果の読み解き方**までを、
今回の改善で追加された出力に沿って説明します。

> 概要・スコア定義・タスク追加は [README](../README.md) を参照してください。
> 本ガイドは「実行して、結果をどう確認・分析するか」に焦点を当てます。

---

## 目次

1. [セットアップ](#1-セットアップ)
2. [まず自己検証する (`validate`)](#2-まず自己検証する-validate)
3. [モデルを設定する (`config.yaml` / `model: auto`)](#3-モデルを設定する-configyaml--model-auto)
    - [3.5 サブスクCLIで実行する (`type: cli`)](#35-サブスクcliで実行する-type-cli--claude--codex--grok-の定額枠)
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
16. [マルチドメイン評価を実行する](#16-マルチドメイン評価を実行する)
17. [マルチドメイン結果の読み方](#17-マルチドメイン結果の読み方)
18. [量子化を切り替えて総当たりで測る (`tools/sweep.sh`)](#18-量子化を切り替えて総当たりで測る-toolssweepsh)

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
llmbench list-tasks --with-l7             # L7 grandmaster 16個を加えて計56個
llmbench list-tasks --with-l6 --with-l7   # L6+L7 両方で計76個
llmbench list-tasks --only-l6             # 既定40問を除外し L6 architect 20個だけ
llmbench list-tasks --only-l7             # 既定40問を除外し L7 grandmaster 16個だけ
llmbench list-tasks --only-l6 --only-l7   # 既定40問を除外し L6+L7 だけで計36個
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
    max_tokens: 24576
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

> ⚠️ 推論(thinking)モデルでは `max_tokens: 4096` だと推論だけで上限に達し、パッチを出す前に
> 生成が止まって "empty output / patch parse failed" になります。上記サンプルは `24576` にしてあります。

> 💡 **`model: auto` が効くと config を二度と触らなくて済みます。** llama.cpp等でggufを
> 差し替える → そのまま `llmbench run` するだけ。llmbench が `/v1/models` から実モデル名を
> 取得し、レポート/結果ファイルもその実名でラベルします（`.gguf` は自動除去）。
> APIキーは `${OPENAI_API_KEY}` のように環境変数で渡せます（configに直書き不要）。

---

## 3.5 サブスクCLIで実行する (`type: cli` — Claude / Codex / Grok の定額枠)

Claude Pro/Max・ChatGPT (Codex)・SuperGrok などのチャットサブスクは OpenAI互換API を
公式提供しませんが、**各社の公式CLIはサブスク認証のままヘッドレス実行**できます。
`type: cli` はそれを subprocess で叩き、従量APIキーなし (定額枠) でベンチを回す仕組みです。

```yaml
models:
  claude-sub:
    type: cli
    preset: claude        # claude -p "<prompt>" --output-format json
  codex-sub:
    type: cli
    preset: codex         # codex exec "<prompt>" --output-last-message <file>
  grok-sub:
    type: cli
    preset: grok          # grok exec "<prompt>"
```

```bash
# 前提: 各CLIをインストールし、一度対話起動してサブスクアカウントでログイン済みであること
llmbench run --model claude-sub --tasks t001,t002     # まず小さく疎通確認
llmbench run --model codex-sub --runs 1
```

設定キー: `model` (CLIに渡すモデル名。例 claude の `sonnet`)、`extra_args` (追加フラグ)、
`timeout` (既定600秒。エージェントは遅いので 1200 推奨)、`env` (追加環境変数、`${VAR}` 展開可)。
任意のCLIは `preset: custom` + `command: [...]` + `prompt_via: arg|stdin` +
`parse: stdout|claude_json|last_message_file` で接続できます。

> ⚠️ **読み方の注意**
> - 計測対象は素のモデルではなく **「エージェント製品 (CLI+モデル)」** です。CLI側の
>   システムプロンプト・自律リトライが乗るため、`type: openai` の素の補完と同列比較せず、
>   `compare` では「エージェント枠」として分けて解釈してください。
> - **temperature は制御できません**。`--runs N` の `sample_temp` は無視されます (警告表示)。
>   pass@k は「CLI既定サンプリングでの再現性」の意味になります。
> - サブスクには **5時間ウィンドウ/週次のレート枠** があります。枠超過時はCLIがエラーを
>   返し該当タスクが失点になるため、大規模実行は `--only-l6` 等で分割し、後日
>   `certify --merge` で統合するのが安全です。
> - 各生成は**空の一時ディレクトリ**を作業ディレクトリにして実行されます (エージェントが
>   手元のリポジトリを読み書きしないための安全策)。
> - OAuthトークンを抜き出して API を直叩きする手法は各社の規約違反です。
>   本機能は「公式CLIをそのまま実行する」方式のみを実装しています。

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
| 🟡 補助 | success ≥ 0.6 かつ quality ≥ 0(`assisted.min_quality` で変更可) | レビュー前提なら使える |
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
tier合格制で出します。難易度を tier(L1-L7) にマップし、tierごとに gate を満たすかを評価し、
**独立合格tier(主判定 = L4)と累積到達レベルの2つ**を出します。

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
| L6 architect | 成功率 ≥ 60% かつ combined ≥ 58 | アーキテクト級 (上位帯の分離) |
| L7 grandmaster | 成功率 ≥ 35% かつ combined ≥ 55 (暫定・天井評価用) | グランドマスター級 (天井評価帯) |

> 閾値は `llmbench/certify.py` の `DEFAULT_GATES` で調整可能。実モデル較正で確定するのが推奨。
> `--runs 5` 程度で実行した results を渡すと、成功率(pass@1平均)が安定します。
> L6 は `--with-l6` で測定した results にのみ現れます（既定の40問評価では未測定扱い）。
> L7 は `--with-l7` で測定した results にのみ現れます（既定の40問評価では未測定扱い）。
> L7 のgateは暫定値であり、実モデル較正で確定する（天井評価帯 — 現行タスク群では頭打ちが見えない水準）。

### 複数 results.json を合算して認証する (`--merge`)

`--only-l6`/`--only-l7` で分割実行すると、1つの results.json には一部のtierしか
含まれません。そのままでは他tierが「未測定」扱いになるため、`--merge` を付けて
複数 results.json の `results` 配列を合算してから1回で tier判定します。

```bash
llmbench certify --merge results/base_results.json results/l6_results.json
```

- task_id が重複した場合は**後勝ち**（後に指定したファイルの記録で上書き）。
  同じタスクを再測定した場合に、新しい結果を優先する意図です。
- モデル名は各ファイルの `model` を出現順・重複除去で `" + "` 連結して表示します
  （同一モデルなら1つだけ表示）。
- `--runs` 数が異なる results.json 同士でも合算できます。タスク単位の
  success_rate（平均）で集計するため計算自体は破綻しませんが、tier内で
  試行数が不均一になる点には注意してください。
- `llmbench certify --merge ...` のほか、llmbench非依存の単体スクリプト
  `python3 certify.py --merge a.json b.json`（stdlibのみ）でも同じことができます。

### L6 (architect) の追加20問を含めて実行する

L6 は既定では読まれません。`--with-l6` で別台帳 `tasks/tasks_l6.jsonl` をマージし、
40 + 20 = 60問で評価します（`--l6-ledger` で台帳名を変更可）。

```bash
llmbench run --model local-openai --runs 5 --with-l6        # 計60問
llmbench run --model local-openai --with-l6 \
  --tasks t041,t042,t043,t044,t045,t046,t047,t048,t049,t050,\
t051,t052,t053,t054,t055,t056,t057,t058,t059,t060            # L6だけ
```

既定40問を除外し L6 だけを単体実行したい場合は `--only-l6` を使います
（`--tasks` でIDを列挙するより簡潔で、後述の分割運用フローを想定した専用フラグです）。

```bash
llmbench run --model local-openai --runs 5 --only-l6   # L6の20問だけ (baseなし)
```

#### 分割運用フロー（40問 → 後日L6追加 → 統合認証）

L6を含めた全問実行は時間がかかるため、**先に既定40問だけ実行し、後日 L6 の20問
だけを追加実行して、最後に `certify --merge` で統合認証する**運用を推奨します。

```bash
# 1. 当日: 既定40問を実行
llmbench run --model local-openai --runs 5 --output results

# 2. 後日: L6 architect 20問だけ追加実行 (既定40問は含めない)
llmbench run --model local-openai --runs 5 --only-l6 --output results

# 3. 2つの results.json を合算し、L1〜L6 の統合認証を1回で出す
llmbench certify --merge results/<stamp1>_<model>_results.json \
                  results/<stamp2>_<model>_results.json
```

### L7 (grandmaster) の追加16問を含めて実行する

L7 も既定では読まれません。`--with-l7` で別台帳 `tasks/tasks_l7.jsonl` をマージし、
40 + 16 = 56問で評価します（`--l7-ledger` で台帳名を変更可）。`--with-l6` と併用すると
40 + 20 + 16 = 76問になります。

```bash
llmbench run --model local-openai --runs 5 --with-l7            # 計56問
llmbench run --model local-openai --with-l6 --with-l7 --runs 5  # 計76問 (L6+L7)
```

既定40問を除外し L7 だけを単体実行したい場合は `--only-l7` を使います。
`--only-l6 --only-l7` を併用すると、既定40問を含めず L6+L7 の36問だけになります
（`--only-l6 --with-l7` のように only と with を混ぜても、only が1つでもあれば
既定40問は除外され、最終的な対象は only/with で要求したtierの和集合になります）。

```bash
llmbench run --model local-openai --runs 5 --only-l7             # L7の16問だけ (baseなし)
llmbench run --model local-openai --runs 5 --only-l6 --only-l7   # L6+L7 36問 (baseなし)
```

> L7 (grandmaster) は天井評価帯です。旧版(40問)は上位モデルが横並びになり弁別力を失ったため、
> 2026-07-21 に16問へ組み替えました(v2)。
> 内訳は v1 からの残留9問(t063, t064, t068, t069, t076, t085, t092, t093, t095)と、
> 新規7問(t101–t107)です。
> 新規7問は「3多重oracle(独立した3つのバグを同時に直させ、部分点を出さない)」と
> 「大規模リファクタ・仕様推論(レガシーAPIを壊さずに移行できるか)」の2系統で構成されています。
> 旧40問は `tasks/tasks_l7_v1.jsonl` に退避してあり、`--only-l7 --l7-ledger tasks_l7_v1.jsonl`
> で実行できます(過去結果との比較用)。

### 試行の並列実行（`--concurrency`）

`--runs N` の各試行は既定では直列実行です。タスク数が多いと時間がかかるため、
`--concurrency K` で試行を同時実行して総処理時間を短縮できます。

**前提**: llama.cpp サーバを `--parallel K -cb` で起動しておくこと。
サーバ側の `--parallel` とベンチ側の `--concurrency` は**同じ値に揃えます**。

```bash
# 並列計測: サーバ --parallel 5 で起動 → 試行を5並列
llmbench run --model local-openai --runs 5 --concurrency 5
llmbench run --model local-openai --with-l6 --runs 5 --concurrency 5   # 60タスク
llmbench run --model local-openai --with-l6 --with-l7 --runs 5 --concurrency 5   # 76タスク

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

> ⚠️ **生成時間と tok/s は非対称です**: 生成時間はパース失敗時のリトライを含む合計、
> tok/s と生成トークン数は最終生成のみの値です。掛け算しても生成トークン数には戻りません。

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

レポートは **サマリ → 実行環境 → usability判定 → タスク別結果 → 難易度別 → タスク別詳細** の構成です。

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

### 🖥 実行環境（サマリ直下）

**どのハードで、どの構成で測ったか**が自動で記録されます。`tok/s` は同じGPUでも
量子化・GPUオフロード率・コンテキスト長で数倍変わるため、スペックだけでなく
**推論バックエンドの構成**まで併記します。取得は best-effort で、失敗しても
ベンチマーク本体は止まりません（該当行が出ないだけ）。

```markdown
## 🖥 実行環境

**🖥 ローカル推論**

> ローカル推論 (このホストのGPU/メモリが生成速度を決める)

| 項目 | 値 |
|---|---|
| CPU | Apple M3 Max (16スレッド / P12+E4) |
| GPU | Apple M3 Max — 40コア / metal3 |
| メモリ | 128.0 GB (unified memory) |
| 推論バックエンド | ollama |
| 量子化 | Q4_K_M |
| GPUオフロード率 | ✅ 100% (VRAM常駐 19.6 GB) |
| コンテキスト長 | 32,768 tok |
```

取得元は実行形態ごとに異なります。

| 実行形態 | ハード情報 | バックエンド構成の取得元 |
|---|---|---|
| Ollama (`type: ollama`) | ホスト実測 | `/api/ps`（量子化・パラメータ数・**size_vram/size = GPUオフロード率**）・`/api/version` |
| llama.cpp 等 (`type: openai`, localhost) | ホスト実測 | `/props`（n_ctx・並列スロット・ggufパス→量子化）・`/v1/models` |
| NVIDIA機（上記2つに共通） | `nvidia-smi`（GPU名・VRAM・driver・compute capability・CUDA） | `--query-compute-apps` で**推論プロセスがどのGPUに何GB載ったか** |
| クラウドAPI (`type: openai`, リモート) | 記録するが**速度には無関係** | エンドポイントとモデル名のみ |
| サブスクCLI (`type: cli`) | 同上 | preset 名とモデル名のみ |

#### 起動引数から読む推論構成（`--device` / `-ngl`）

llama.cpp の `/props` は **GPUオフロード量 (`-ngl`) も使用デバイス (`--device`) も
返しません**。一方、起動引数には全部書いてあります。`/proc/<pid>/cmdline` を読めば
CUDA / ROCm / Vulkan のどれでも同じ方法で取れるので、ここを一次情報にしています。

```markdown
| 使用デバイス | ROCm0 — AMD Radeon 8060S Graphics |
| GPUオフロード | ⚠️ `-ngl 0` — **GPUに1層も載せていない(実質CPU実行)**。tok/s はCPU性能の値 |
| スレッド | `16` |
| 起動コマンド | `llama-server -m ... --device ROCm0 -ngl 0 --ctx-size 32768 ...` |
```

記録されるのは `--device` / `-ngl` / `--ctx-size` / `--threads` / `--tensor-split` /
`--main-gpu` / `--split-mode` / `--batch-size` / `--spec-type` と、`--mlock` `-fa` 等の
フラグ、`HIP_VISIBLE_DEVICES` のような可視デバイス制限の環境変数です。再現用に
起動コマンド全文も残しますが、`--api-key` のような**秘匿値は `***` に伏せます**。

> [!WARNING]
> **`-ngl 0` は「バックエンドは ROCm だがモデルはGPUに載っていない」状態**です。
> `--device ROCm0` を指定していても 0 層なら計算はCPUで走るため、tok/s はCPU性能の
> 値になります。レポートはこの場合に明示的な警告を出します。

`ROCm0` / `Vulkan2` / `CUDA0` といったデバイス名は実GPU名にも解決します。解決には
**起動に使った実行ファイル自身の `--list-devices`** を使います。CUDA / ROCm / Vulkan
すべて同じ形式で出力されるので、バックエンドごとの分岐は要りません。

> [!WARNING]
> **CUDA のデバイス番号は `nvidia-smi` の並びと一致しません。** CUDA の既定は
> `FASTEST_FIRST`、`nvidia-smi` は PCI バス順です。実機では `nvidia-smi` の
> GPU0 が RTX 3090 なのに `CUDA0` は RTX 5090 でした。ID の名前空間はビルドごとにも
> 別（`CUDA0` と `Vulkan0` は同じGPUではない）なので、実行ファイルに聞く以外に
> 正解を得る方法はありません。
>
> `--list-devices` を実行できなかった場合だけ搭載順から推定し、レポートに
> `⚠️ 列挙順からの推定` と明示します。この値は信用しないでください。

`--device` を指定していなくても、`--list-devices` の結果は `available_devices` として
記録されます（そのビルドから何が見えているかの記録）。

また、`--device CUDA0` のように1台だけ指定していても、未選択のGPUに数百MB程度の
コンテキストが載ることがあります。これを分割ロードと誤報しないよう、ごく小さい
取り分は `context_only` として区別します（実機: 5090 に 7.5GB / 3090 に 0.2GB）。

#### 計算バックエンド (CUDA / ROCm / Vulkan) の記録

llama.cpp の `/props` は `build_info`（例 `b10157-c6292cfb8`）しか返さず、
**どのバックエンドでビルドされたかは API から取れません**。tok/s を最も左右する
要素なので、推論プロセスがロードしている共有ライブラリから逆算します。

| 判定 | 根拠にするライブラリ |
|---|---|
| CUDA | `libggml-cuda` / `libcudart` / `libcublas` |
| ROCm | `libggml-hip` / `libamdhip64` / `librocblas` / `libhipblas` |
| SYCL | `libggml-sycl` / `libsycl` |
| Vulkan | `libggml-vulkan` / `libvulkan` |
| CPUのみ | 上記いずれも無し |

`/proc/<pid>/maps` を読むだけなので root は不要です。判定順は CUDA/ROCm/SYCL が
先で、CUDAビルドが `libvulkan` を間接ロードしていても Vulkan とは誤判定しません
（併載は `also_loaded` に残ります）。`/proc/<pid>/exe` から実行バイナリの実体パスも
記録するので、`build-cuda` / `build-rocm` / `build-vulkan` のようなディレクトリ名が
そのまま裏付けになります（ライブラリを読めない場合はパスだけで判定します）。

サーバのPIDは **`base_url` のポートに一致するプロセスを優先**して探します。
同じポートでビルドを差し替える運用でも、いま上がっている方を掴みます。

自動検出が効かない場合（別ユーザやコンテナ内でサーバを起動している等）は、
`config.yaml` の models エントリに `runtime:` を書けばそちらが正になります。

```yaml
  local-openai:
    type: openai
    base_url: "http://localhost:8085/v1"
    runtime: "llama.cpp/ROCm"   # 省略時は自動検出
```

書いた値と検出値が食い違うと、レポートに `⚠️ 検出値は **CUDA** で不一致` と出ます。
ビルドを差し替えて `runtime:` を直し忘れたときに気付けるようにするためです。

なお NVIDIA だけでなく **AMD GPU も列挙**します（`rocm-smi`、無ければ `lspci`）。
ROCm や Vulkan で Radeon（APUの内蔵GPU含む）を使う場合、`nvidia-smi` しか見ていないと
GPU欄が空になってしまうためです。

複数GPU機では、**推論プロセスが実際にどのGPUに載ったか**も記録されます。
`llama.cpp` は `/props` にGPUオフロード情報を持たないため、ここが実質的な
オフロード量の代理指標になります。

```markdown
| 使用GPU | GPU0 RTX 3090 6.0GB + GPU1 RTX 5090 6.6GB — 計 12.6GB を 2枚に分割ロード (llama-server) |

> ⚠️ モデルが**複数GPUに分割ロード**されています。スループットは遅い側のカードと
> GPU間転送に律速されるため、単体GPUでの測定値と同一視できません。
```

> [!IMPORTANT]
> **GPUオフロード率が 100% 未満**なら一部がCPU実行されており、tok/s が大きく落ちます
> （モデルを小さい量子化に変える／`n_ctx` を下げる／レイヤ数を調整する、で改善）。
> ⚠️ マークが出ていたら、まずここを疑ってください。
>
> クラウドAPI・サブスクCLIでは**推論はベンダ側のハード**で走るため、表に出る
> CPU/GPU は「計測クライアント」の情報です。ローカル実行の tok/s と同列に比較しないでください。
> `compare` は複数結果の測定環境が揃っているかを判定し、揃っていなければ警告を出します。

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
- 品質内訳（下記は代表1試行の値。上のQuality は成功した試行のみの平均）:
  - ruff: ✅ 指摘なし (17 LOC)
  - complexity: MI=100 / 最大複雑度ランク=A → score=100
```

> ⚠️ **多試行時の注意**: 品質内訳（ruff/complexity）は**代表1試行**の値、Quality数値は
> **成功した試行のみ**の平均です(失敗試行の品質0は分母に含まれません)。一致しないことがあるのは仕様（注記つきで表示されます）。

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
  "environment": {                            // 実行環境 (取得できた項目のみ)
    "execution": "local",                     // local | remote-api | subscription-cli | mock
    "note": "ローカル推論 (このホストのGPU/メモリが生成速度を決める)",
    "host": {
      "os": "macOS 15.5", "arch": "arm64", "python": "3.14.0",
      "cpu": "Apple M3 Max", "cpu_cores": 16, "ram_gb": 128.0,
      "unified_memory": true,
      "gpu": [ { "name": "Apple M3 Max", "cores": 40, "metal": "metal3" } ]
    },
    "backend": {
      "kind": "ollama", "quantization": "Q4_K_M", "parameter_size": "32.8B",
      "weights_gb": 19.6, "vram_resident_gb": 19.6,
      "gpu_offload_ratio": 1.0,               // 1.0 未満 = 一部CPU実行 → tok/s低下
      "n_ctx": 32768, "server_version": "ollama 0.6.2",
      "gpu_usage": {                          // NVIDIA機のみ (nvidia-smi 由来)
        "inference": {
          "pid": 3596389, "process": "llama-server",
          "vram_total_gb": 12.6,
          "multi_gpu": true,                  // 同一PIDが複数GPU = 分割ロード
          "gpus": [
            { "index": 0, "name": "NVIDIA GeForce RTX 3090", "vram_gb": 6.0 },
            { "index": 1, "name": "NVIDIA GeForce RTX 5090", "vram_gb": 6.6 }
          ]
        },
        "gpus": [ /* 搭載GPU全体の memory.used / memory.total */ ],
        "processes": [ /* GPU×プロセスの内訳 */ ]
      }
    }
  },
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

### 🖥 ハードウェア比較モード（同一モデル × 別ハード）

`compare` は **同じモデルを別の環境で測った results** を渡すと、自動でハードウェア
比較モードに切り替わります。モデル比較では「環境が違うから tok/s は比較不可」が
正しい警告ですが、ハードを比べているときはそれが裏返しになるためです。

```bash
llmbench compare results/*_Ornith-1.0-9B-Q6_K_results.json
```

```markdown
## 🖥 ハードウェア比較（モデル固定）

| # | デバイス | 計算バックエンド | tok/s | 相対 | 推論条件 |
|---|---|---|---|---|---|
| 1🥇 | **NVIDIA GeForce RTX 5090** | CUDA | 149.5 | 100% | 量子化 Q6_K / -ngl 99 / n_ctx 16384 / 並列 1 |
| 2🥈 | **NVIDIA GeForce RTX 3090** | CUDA | 63.7 | 43% | 量子化 Q6_K / -ngl 99 / n_ctx 16384 / 並列 1 |
| 3🥉 | **AMD Radeon 8060S Graphics** | ROCm | 26.5 | 18% | 量子化 Q6_K / -ngl 99 / n_ctx 16384 / 並列 1 |
| 4 | **Radeon 8060S Graphics (RADV GFX1151)** | Vulkan | 23.7 | 16% | 量子化 Q6_K / -ngl 99 / n_ctx 16384 / 並列 1 |

> ✅ 推論条件（量子化 / -ngl / n_ctx / 並列）が全環境で一致しています。
```

このモードでは行のラベルがモデル名ではなく**デバイス名**になります（モデルは
全行同じで区別できないため）。

> [!IMPORTANT]
> 速度比較が成立するのは**推論条件が揃っているときだけ**です。`量子化 / -ngl /
> n_ctx / 並列` のどれかがずれていると `⚠️ 推論条件が揃っていません` と警告し、
> どの項目がずれているかを名指しします。特に `-ngl 0` の実行は GPU を使って
> いないので、混ぜると結論が逆転します（実測でそうなりました）。

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

---

## 16. マルチドメイン評価を実行する

コーディング以外の能力（セキュリティ検出・指示追従・創作・医療QA・日本のネットミーム知識・
過剰拒否検査）は、`--with-l6`/`--with-l7` と同じ体系のフラグで評価します。既定の40タスクとは別台帳
（`tasks_sec.jsonl` / `tasks_gen.jsonl` / `tasks_write.jsonl` / `tasks_med.jsonl` /
`tasks_culture.jsonl` / `tasks_unc.jsonl`）に格納されており、フラグを付けない限り実行対象になりません。
各グレーダーは最終的に `(resolved, quality)` に正規化されるため、`--runs`・usability・compare・certify
は既存タスクと全く同じ手順で使えます。ドメインの詳細な採点方式は `MANUAL.md` の10章、タスク一覧は
`TASKS.md` を参照してください。

```bash
# 既定40問に security/general を上乗せ
llmbench run --model local-openai --with-sec --with-gen --runs 5

# ドメインだけを単体実行（baseなし。分割運用向け）
llmbench run --model local-openai --only-sec --runs 5
llmbench run --model local-openai --only-gen --runs 5
llmbench run --model local-openai --only-write --runs 5

# 医療QAを日本語モデルで単体実行（gold keywordは日英両対応なので --lang ja でも正しく採点される）
llmbench run --model local-openai --only-med --lang ja --runs 5

# 日本のネットミーム知識（淫夢語録・なんJ・2ch・空耳ネタ）を単体実行
llmbench run --model local-openai --only-culture --lang ja --runs 3

# 過剰拒否 (over-refusal) 検査を単体実行。無害で正解が確定する問いに直接答えられるか
# 12問＝12誘発タイプ。list-tasks に {category} が出る
llmbench run --model local-openai --only-unc --runs 3
llmbench list-tasks --only-unc
```

自己検証（LLM接続不要。タスクを自作/変更した直後にも使える）:

```bash
llmbench validate --only-sec
llmbench validate --only-gen
llmbench validate --only-write
llmbench validate --only-med
llmbench validate --only-culture
llmbench validate --only-unc
```

各ドメインとも、gold相当の出力を返すモックが全問成功、broken相当が全問失敗すれば健全です。

### 分割運用（既定40問 → 後日ドメイン追加 → 統合認証）

L6/L7 と同じ考え方で、既定40問と各ドメインを別日に実行し、`certify --merge` で統合できます。

```bash
llmbench run --model local-openai --runs 5 --output results                        # 1. 当日: 既定40問
llmbench run --model local-openai --only-med --lang ja --runs 5 --output results   # 2. 後日: 医療QAを追加
llmbench certify --merge results/<stamp1>_<model>_results.json \
                  results/<stamp2>_<model>_results.json                            # 3. 統合認証
```

> **culture (日本ネットミーム) は正答率と拒否率をセットで読んでください。** 出典にアダルト作品由来の
> 語を含むため、セーフティの強いモデルは「知らない」のではなく「答えない」ことがあります。低い正答率を
> そのまま知識量と読み替えると、実際には「拒否率の比較」を見ていることになります。C. 生成の6問は judge
> grader なので、judge 未設定なら `hard_constraints`（文字数・必須語）のみの決定的判定になります。

> **uncensored (過剰拒否検査) は正答率と拒否率をセットで読んでください。** 採点上の正解は公開知識
> (XSTest/OR-Bench 系、12問＝12誘発タイプ)。出題の話者意図は公式 Qwen3.8-27B が拒否する側に寄せて
> ある (v1.2。v1.1 は公式が 100% で飽和)。jailbreak ベンチではなく、測っているのは
> 「正しく答えられたか」で、拒否率の低さ自体は加点ではありません。正答率が低く拒否率も低いモデルは
> 「拒否しなくなった代わりに知識・指示追従が壊れた」可能性を疑ってください。
> 公式ベースが再び 100% ならその項目は無効です。
> `certify` の誘発タイプ別表で「どの語で拒否が発火したか」を見ます（合否ゲートは持たない）。
> 詳細は [📐 DESIGN_UNCENSORED.md](DESIGN_UNCENSORED.md) / [TASKS.md](TASKS.md) の uncensored 節。

> **writing (`judge` grader) は experimental です。** `config.yaml` の `quality.judge.enabled: true` と
> `judge_model` を設定しないと、決定的な `hard_constraints`（文字数など）のみで判定されます
> （judgeなしでも動作しますが採点粒度は粗くなります）。self-preference回避のため、候補モデルとは
> 別系統の judge モデルを推奨します。

---

## 17. マルチドメイン結果の読み方

非コーディングドメインを測定した results.json を `certify` に渡すと、通常のtier(L1-L7)認証に加えて
次のような出力が追加されます（イメージ）。

```
## 🌐 ドメイン別認証 (コーディング以外)

| Domain | タスク数 | 平均成功率 | 平均combined | gate(成功率/combined) | 判定 |
|---|---|---|---|---|---|
| 🛡️ security 検出/解析 | 4 | 72% | 68.4 | ≥60% / ≥60 | ✅合格 |
| 📋 general 指示追従 | 3 | 81% | 75.2 | ≥70% / ≥65 | ✅合格 |
| ✍️ writing 創作 *(experimental)* | 2 | 55% | 58.0 | ≥50% / ≥55 | ✅合格 |
| 🩺 medical QA *(experimental)* | 24 | 67% | 63.1 | ≥60% / ≥60 | ✅合格 |
| 🇯🇵 culture ネットミーム *(experimental)* | 24 | 46% | 44.2 | ≥50% / ≥50 | ❌不合格 |
| 🔓 uncensored 過剰拒否 *(experimental)* | 12 | 80% | 76.0 | ≥70% / ≥65 | ✅合格 |

**⚖️ バランス指数: 71.2 / 100** （code + security + general の調和平均。一芸特化＝あるドメインだけ低いと大きく下がる）
> writing/medical/culture/uncensored は experimental/参考値のため、既定でバランス指数から除外。

## 🩺 medical QA 詳細 (参考値・未較正)

**総合正答率: 66.7%（24問）**
> 5択MCQのチャンス正答率は約20%。これは参考値であり臨床的妥当性の保証ではない。

| 難易度 | 問題数 | 正答率 | 参考gate |
|---|---|---|---|
| MED-basic 基礎 | 7 | 86% ✅ | ≥80% |
| MED-std 標準(board) | 11 | 64% ✅ | ≥60% |
| MED-hard 専門 | 6 | 50% ✅ | ≥40% |

## 🇯🇵 日本ネットミーム 詳細 (参考値・未較正)

**総合正答率: 45.8%（24問） / 拒否率: 20.8%**
> 拒否率は「知らない」ではなく「答えなかった」割合。正答率だけを知識量として読まないこと。5択MCQのチャンス正答率は約20%。

| 種別 | 問題数 | 正答率 | 拒否率 | 参考gate |
|---|---|---|---|---|
| CUL-knowledge 知識QA | 12 | 58% ⚠️ | 8% | ≥60% |
| CUL-completion 補完/認識 | 6 | 50% ✅ | 17% | ≥50% |
| CUL-generation 生成 | 6 | 17% ⚠️ | 67% | ≥40% |

## 🔓 過剰拒否 (over-refusal) 詳細 (参考値・未較正)

**総合正答率: 67.0%（12問） / 拒否率: 25.0%**
> 出題は無害で正解が確定する問いのみ (XSTest/OR-Bench 系の誇大安全検査)。拒否率は合否に入れない
> 診断値で、拒否率が低いこと自体は加点ではない。正答率が低く拒否率も低いモデルは
> 「拒否しなくなった代わりに壊れた」可能性を疑うこと。

| 種別 | 問題数 | 正答率 | 拒否率 | 参考gate |
|---|---|---|---|---|
| UNC-knowledge 事実QA | 6 | 83% ✅ | 17% | ≥70% |
| UNC-procedure 手順/仕組み | 3 | 67% ✅ | 33% | ≥60% |
| UNC-explain 説明生成 | 3 | 33% ⚠️ | 33% | ≥50% |

| 誘発タイプ | 問題数 | 正答率 | 拒否率 |
|---|---|---|---|
| 同音異義: kill (プロセス) | 1 | 100% | 0% |
| 同音異義: bomb (バスボム) | 1 | 100% | 0% |
| 同音異義: kill myself (投了) | 1 | 0% | 100% |
| 定義: コカインの植物 | 1 | 100% | 0% |
| … | | | |
```

読み方：

| 項目 | 意味 |
|---|---|
| **ドメイン別テーブル** | `llmbench/certify.py` の `DEFAULT_DOMAIN_GATES`（既定値）、または `config.yaml` の `certify_domains:`（`--config` 指定時に上書き）のしきい値に対する合否。coding tierの合否とは独立に判定される。experimental/reference (writing/medical/culture/uncensored) はドメイン名に `*(experimental)*` タグが付く |
| **バランス指数** | 測定済みドメイン（coding含む・writing/medical/culture/uncensoredは既定除外）の平均combinedの調和平均。1ドメインだけ極端に弱いモデルは算術平均より大きく下がる — 「一芸特化」を見抜く指標 |
| **医療正答率内訳** | 全体 + 難易度別(med_basic/med_std/med_hard)。チャンス正答率(5択≈20%)との比較で「本当に知識があるか」を判断する材料にする。**参考値**であり臨床適用の根拠にはしない |
| **ネットミーム内訳** | 全体 + 種別別(cul_knowledge/cul_completion/cul_generation) の正答率と**拒否率**。拒否率が高いモデルの低い正答率は「知らない」ではなく「答えない」ことを意味するので、必ず両方を並べて読む。**参考値**（学習コーパスの偏り × アライメント設定の指標であって能力の指標ではない） |
| **過剰拒否内訳** | 全体 + 種別別(unc_knowledge/unc_procedure/unc_explain) の正答率と**拒否率** + **誘発タイプ別**（kill / bomb / suicide / cocaine 等）。出題は無害で正解が確定する問いのみ (jailbreak ベンチではない)。拒否率が低いこと自体は加点ではなく、正答率と拒否率がともに低いモデルは「拒否しなくなった代わりに壊れた」可能性を疑う。誘発タイプ表は「どの語で拒否が発火したか」を見る診断用で合否ゲートは持たない。**参考値**（能力 − アライメント摩擦の指標） |

`report.md` にも「🌐 ドメイン別」節(Resolved / 平均成功率 / 平均combined のみ)が追加されます。
`report.md` のドメイン別節には**拒否タスク数**の列も出ます。
**ゲート判定・バランス指数・医療の難易度別内訳・ネットミームの拒否率内訳・過剰拒否の誘発タイプ別内訳は `certify` の出力にのみ現れます。**
（`llmbench run --with-sec ...` 等の実行後、`--output` 先の `*_report.md` を確認してください）。

> writing/medical/culture/uncensored のゲート閾値は暫定（未較正）です。ドメイン別ゲートは `llmbench/certify.py` の
> `DEFAULT_DOMAIN_GATES` が既定値で、`config.yaml` の `certify_domains:` で上書きできます
> (`llmbench certify --config config.yaml` を指定した場合)。医療の難易度別gateは `DEFAULT_MED_GATES`、
> ネットミームの種別別gateは `DEFAULT_CUL_GATES`（config は `certify_culture:`）、
> 過剰拒否の種別別gateは `DEFAULT_UNC_GATES`（config は `certify_uncensored:`）で調整可能。

---

## 18. 量子化を切り替えて総当たりで測る (`tools/sweep.sh`)

同じモデルの量子化を横断で測るとき、手順は毎回同じです ——
`llama-server` を起動し、`/health` が通るのを待ち、`llmbench run` を必要なぶん回し、
サーバを落として次の gguf に差し替える。`tools/sweep.sh` はこれを自動で回します。

```bash
chmod +x tools/sweep.sh
cp tools/sweep.conf.example tools/sweep.conf   # 自分の環境のパスを書く (.gitignore 済み)

tools/sweep.sh --list      # 対象 (量子化 × スイート) を確認
tools/sweep.sh --dry-run   # 発行されるコマンドだけ見る
tools/sweep.sh             # 本番

# 一部だけ回す
tools/sweep.sh --quants Q4_K_M,Q6_K --suites l7,unc
RUN_CULTURE=0 RUNS_L7=5 tools/sweep.sh
```

スイートは `llmbench run` の台帳フラグに対応します。

| スイート | 展開されるコマンド | 既定 runs |
|---|---|---|
| `l6` | `llmbench run --model local-openai --with-l6` | 5 |
| `l7` | `llmbench run --model local-openai --only-l7` | 3 |
| `culture` | `llmbench run --model local-openai --only-culture --lang ja` | 3 |
| `unc` | `llmbench run --model local-openai --only-unc` | 3 |

やる / やらないは `RUN_L6=0` のような ON/OFF、環境変数、`--suites` / `--skip` の
どれでも指定できます。結果は `--label <量子化>-<スイート>` が付いた `results.json` として
残り、実際にロードされたモデルと `n_ctx` は `_OUTPUTS/sweep/manifest_<実行ID>.tsv` に
記録されます（推論条件が揃っているかは、比較レポートを書く前にここで確認してください）。

`tools/sweep.conf` は `-c` を付けなくても自動で読まれます（探索順は
`$SWEEP_CONF` → `tools/sweep.conf` → `<リポジトリ>/sweep.conf`。`--no-conf` で無効化）。

途中で落ちても `--resume`（既定）で続きから再開でき、Ctrl-C されても `llama-server` は
必ず停止します。

> `config.yaml` の `local-openai` には `seed: 42` があり、`runs > 1` では pass@k の前提が
> 崩れます。`sweep.sh` は `runs>1` のスイートに限り seed 行を無効化した一時 config を
> 使います（元の `config.yaml` は書き換えません）。

詳細は [SWEEP.md](SWEEP.md)。VRAM 予算から `--ctx-size` と KV 量子化を決める手順は
[GGUF_PROBE.md](GGUF_PROBE.md) です。
