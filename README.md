<div align="center">

# 🧪 llmbench

**ローカルLLMは本当に"使える"のか? — 機能正確性 × コード品質で測るSWE-Bench風ベンチマーク**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

「テストは通るが汚いコード」と「綺麗で安全なコード」のトレードオフを、<br>
ローカル環境で**ガチ検証**するためのフルスクラッチ・フレームワーク。

[特徴](#-特徴) • [クイックスタート](#-クイックスタート) • [スコアリング](#-スコアリング) • [タスク追加](#-タスクの追加) • [ロードマップ](#-ロードマップ)

</div>

---

## ✨ 特徴

- 🎯 **機能的正確性** — SWE-Bench風。バグレポート + ソースをLLMに渡し、patch適用 → 隠しテスト(pytest)で resolved 判定
- 🧹 **コード品質レイヤー** — Ruff (lint密度) / radon (保守性指数・循環的複雑度) / LLMレビュー採点 / SonarQube を重み付き合成
- 🎲 **信頼性 (pass@k)** — `--runs N` で各タスクをN回試行し、成功率(pass@1)・pass@k・フレ(flaky)を計測。「1回成功＝使える」ではなく**安定して使えるか**を測る
- 🧭 **usability判定** — 信頼性×品質から各タスクを **🟢自律 / 🟡補助 / 🔴不可** に分類し、「実際どれくらい任せられるか」を提示
- 🎓 **使えるライン認証 (`certify`)** — 難易度を tier(L1-L5) にマップし、tierごとの合格判定で「ここまでクリアできれば使える」を提示。**L4(expert)独立合格＝実務投入ライン**
- ⚖️ **複合スコア** — 動かないコードは0点。動くコードを成功率と品質で差別化
- 🔌 **接続自在** — OpenAI互換API (llama.cpp / LM Studio / vLLM) と Ollama 両対応。**`model: auto`** でサーバのロード中モデルを自動採用（config編集不要）、Ollamaは**インストール済みモデルを動的に選択**
- 🆚 **モデル横断比較** — `compare` で複数結果を1枚のランキング・マトリクスに。参照モデル(API)を併置して位置づけ
- 🇯🇵 **日英issue同梱** — `--lang ja` で「language tax」(日本語指示による性能低下)を計測可能
- ⚡ **速度計測** — タスク別レイテンシ / tok/s をレポートに自動記録
- 📦 **同梱タスク40個** — L1 easy 5 / L2 medium 5 / L3 hard 10 / **L4 expert 12 / L5 frontier 8**。上位ローカルコーダーの天井効果を破る難問tier込み。frontierは複数ファイル・回帰罠・性能制約(perf_timeout)を含む。新tierのissueは**症状ベース**で原因診断を要求。外部依存なし(stdlib-only)で即実行
- 🛡️ **安全設計** — テストはLLMに非公開、patch書込先は既知ファイルに限定、元タスクは不変

## 🚀 クイックスタート

```bash
git clone https://github.com/zephel01/swe-bench.git
cd swe-bench
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 1️⃣ 自己検証 (LLM不要 — モックでパイプライン全体を確認)
llmbench validate

# 2️⃣ config.yaml の base_url を自分の環境に。model は "auto" でOK（サーバのモデルを自動採用）

# 3️⃣ 利用可能モデルを確認（config定義 + Ollama稼働モデル）
llmbench models

# 4️⃣ 実行
llmbench run --model local-openai                 # 全40タスク・1回
llmbench run --model local-openai --runs 5        # 各タスク5回 → 成功率・pass@k
llmbench run --model qwen2.5-coder:7b --runs 5    # Ollamaの実モデル名を直接指定もOK
llmbench run --model local-openai --tasks t021,t033 --lang ja   # 新tierだけ実行も可

# 5️⃣ 複数結果を横断比較
llmbench compare results/*_results.json

# 6️⃣ 使えるライン認証 (tier合格制)
llmbench certify results/<stamp>_<model>_results.json
```

サブコマンド: `list-tasks` / `models` / `run` / `compare` / `certify` / `validate`

結果は `results/` に以下の3点で保存されます。

- `<stamp>_<model>_results.json` — スコア・集計 (機械可読、軽量)
- `<stamp>_<model>_report.md` — 人が読むMarkdownレポート
- `<stamp>_<model>_artifacts/<task_id>/` — **生成物そのもの**
  - `llm_output.txt` … LLMの生出力 (パース失敗時の原因確認用)
  - `generated/<path>` … 適用された生成コード (動作確認用)
  - `test_output.txt` … pytest出力 (テスト失敗の原因確認用)

実行中のログにも、タスクごとに生成ファイル・コード冒頭・パース/テスト結果が出力されるので、その場で「ちゃんと動いているか」を確認できます。

> [!TIP]
> 実行ログ・レポート・生成物の**読み解き方**やモデル比較の手順は [📘 利用ガイド (USAGE.md)](USAGE.md) を参照。

<details>
<summary>📄 レポート出力例 (--runs 5)</summary>

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
- 🟢 自律 17/20 (85%) / 🟡 補助 2/20 (10%) / 🔴 不可 1/20 (5%)
> 総合推奨: おおむね自律。ただし🔴不可 1/20 (5%) は要注意

| | Task | 判定 | 信頼性 | Quality | Combined | tok/s |
|---|---|---|---|---|---|---|
| ✅ | t007 | 🟡 補助 | 4/5 (成功率80%) | 100 | 80 | 111.9 |
| ❌ | t020 | 🔴 不可 | 0/5 (成功率0%)  | 0   | 0  | 122.2 |
```

</details>

## 📊 スコアリング

```
combined = success_rate × (0.5 + 0.5 × quality / 100) × 100
```

`success_rate` は試行の成功率（`--runs 1` なら resolved の 0/1、複数試行なら 0.0〜1.0）。
**信頼性がそのままスコアに反映**される（例: 60%成功・品質90 → 0.6×95 = 57点）。

| success_rate | quality | combined | 意味 |
|---|---|---|---|
| 0 (不可) | — | **0** | 動かないコードは品質に関わらず0点 |
| 1.0 | 0 | **50** | 毎回動くが品質最低 |
| 1.0 | 100 | **100** | 毎回動いて品質も完璧 |
| 0.6 (flaky) | 90 | **57** | たまに失敗。信頼性で減点 |

### 信頼性 (pass@k) と usability判定

`--runs N` で各タスクをN回試行し、**成功率(pass@1)** を主指標に、pass@k・フレ(flaky)を計測。
さらに success_rate と quality からタスクを3ティアに分類する (しきい値は `config.yaml` の `usability:`):

| ティア | 既定条件 | 意味 |
|---|---|---|
| 🟢 自律 | success ≥ 0.9 かつ quality ≥ 80 | レビューほぼ不要で任せられる |
| 🟡 補助 | success ≥ 0.6 | レビュー前提なら使える |
| 🔴 不可 | 上記未満 | この種のタスクには任せられない |

### 🎓 使えるライン認証 (`certify`)

usability判定が**タスク単位**なのに対し、`certify` は**モデル全体**を判定する。
難易度を tier(L1-L5) にマップし、tierごとの平均成功率/combinedが gate を満たすかを
**独立に**評価して「到達レベル」を出す。`llmbench certify results/<...>_results.json`。

| Gate | 条件 (tier平均) | 意味 |
|---|---|---|
| L1 easy | success ≥ 90% | おもちゃ級は確実 |
| L2 medium | success ≥ 85% | 仕様準拠の単純作業可 |
| L3 hard | success ≥ 75% かつ combined ≥ 60 | 実務の単純〜中級バグ可 |
| **L4 expert** | **success ≥ 60% かつ combined ≥ 55** | **✅ 使えるライン (監督付き実務投入)** |
| L5 frontier | success ≥ 40% | フロンティア級 |

**使えるライン = L4 を独立に合格**(下位tierの取りこぼしに左右されない)。
閾値は `llmbench/certify.py` の `DEFAULT_GATES` で調整可能。

品質スコアの内訳 (重みは `config.yaml` で自由に変更):

| レイヤー | 既定重み | 内容 |
|---|---|---|
| 🔍 Ruff | 0.4 | E/F/W/B/SIM/C4/S ルールのissue密度で減点 |
| 🌀 radon | 0.3 | Maintainability Index + 最悪CCランクで減点 |
| 🤖 LLMレビュー | 0.3 (任意) | 別LLMが0-10点でコードレビュー |
| 📡 SonarQube | 任意 | サーバ稼働時のみ。重大度別減点 |

## ⚙️ 設定

`config.yaml` で一元管理:

```yaml
models:
  local-openai:            # llama.cpp / LM Studio / vLLM
    type: openai
    base_url: "http://localhost:8080/v1"
    model: "auto"          # auto = /v1/models のロード中モデルを自動採用 (config編集不要)
  local-ollama:
    type: ollama
    base_url: "http://localhost:11434"
    model: "qwen2.5-coder:32b"
  ref-gpt:                 # compareのアンカー用 (API)
    type: openai
    base_url: "https://api.openai.com/v1"
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"   # ${VAR} は環境変数から展開

run:
  issue_lang: en           # ja に切替で language tax 検証
  test_timeout: 120
  runs: 1                  # 各タスクの試行回数 (>1 で pass@k・成功率)
  sample_temp: 0.8         # 複数試行時のサンプリング温度
  # ollama_host: "http://localhost:11434"   # Ollama接続先 (未定義モデルの自動解決)

quality:
  llm_review:
    enabled: false         # レビュー用モデル稼働時に true
    reviewer_model: local-openai

usability:                 # success_rate × quality でティア分類
  autonomous: {min_success: 0.9, min_quality: 80}
  assisted:   {min_success: 0.6, min_quality: 0}
```

> [!TIP]
> **モデル名を毎回書き換える必要はありません。** `model: "auto"` にしておけば、llama.cpp等で
> ggufを差し替えるだけで、llmbench が `/v1/models` から実モデル名を取得し、レポート/ファイル名も
> その実名でラベルします。Ollamaは `--model <インストール済み名>` を直接指定できます
> (`llmbench models` で一覧)。固定したい時は `--label <名前>`。

## 📁 プロジェクト構成

```
swe-bench/
├── llmbench/
│   ├── clients/        # 🔌 LLM接続 (openai_compat / ollama / mock)。model:auto・Ollama一覧
│   ├── patch.py        # 📝 LLM出力パース (FILE:マーカー + コードブロック)
│   ├── sandbox.py      # 📦 一時コピー + pytest隔離実行
│   ├── functional.py   # ✅ resolved判定
│   ├── quality/        # 🧹 ruff / complexity / llm_review / sonar
│   ├── scoring.py      # ⚖️ 複合スコア + pass@k 推定量
│   ├── usability.py    # 🧭 自律/補助/不可 ティア分類
│   ├── certify.py      # 🎓 tier合格制「使えるライン」判定
│   ├── runner.py       # 🎛️ オーケストレータ (多試行集計・モデル解決)
│   ├── compare.py      # 🆚 複数結果の横断比較レポート
│   └── report.py       # 📊 Markdownレポート
├── tasks/              # 🧩 同梱タスク40個 (L1 easy5 / L2 medium5 / L3 hard10 / L4 expert12 / L5 frontier8)
└── config.yaml
```

> [!NOTE]
> patch形式は「ファイル全体置換」(`--- FILE: path ---` + コードブロック) を採用。
> ローカルLLMはunified diffの行番号精度が低いため、この方式の方がパース成功率が高い。

## 🧩 タスクの追加

```
tasks/tXXX_name/
├── issue.md        # 英語バグレポート
├── issue_ja.md     # 日本語バグレポート
├── buggy_code/     # バグ入りソース (LLMに渡される)
├── gold/           # 正解ファイル (変更が必要なファイルのみ)
└── tests/          # 隠しテスト (LLMには渡されない)
```

1. 上記レイアウトでディレクトリを作成
2. `tasks/tasks.jsonl` に1行追加 (難易度は easy/medium/hard/expert/frontier):
   ```json
   {"task_id": "t041", "dir": "t041_name", "difficulty": "expert", "title": "..."}
   ```
   性能制約タスクは `"perf_timeout": <秒>` を足すとそのタスクだけ個別タイムアウトになる。
   回帰罠は `tests/` に複数テストを置く (例: `test_core.py` で既存挙動をロック、
   `test_bug.py` でバグを捕捉)。
3. 検証: `llmbench validate --tasks t041` (gold がpass / broken がfail すればOK)

## 🗺️ ロードマップ

- [x] 機能 + 品質の複合評価パイプライン
- [x] OpenAI互換 / Ollama 両対応
- [x] 日英issueによる language tax 計測
- [x] 🎲 信頼性 (pass@k / 成功率) 計測
- [x] 🧭 usability ティア判定
- [x] 🆚 複数モデル横断比較レポート (`compare`)
- [x] 🔎 `model: auto` / Ollama動的モデル選択
- [x] 🧩 難問tier (L4 expert / L5 frontier) で天井効果を打破 — 計40問
- [x] 🎓 tier合格制「使えるライン」認証 (`certify`)
- [x] ⏱️ タスク別 perf_timeout (性能制約タスク)
- [ ] 🎯 実モデル較正による tier 閾値の確定 (32b dense / 3b級を追加)
- [ ] 🐳 Docker隔離実行
- [ ] 📥 SWE-bench Lite 公式タスクの取込
- [ ] 🔄 GitHub repoからのタスク自動抽出
- [ ] 📈 nvidia-smiによるVRAM自動計測

## 🤝 Contributing

タスク追加・品質レイヤー追加のPR歓迎です。`llmbench validate` がPASSすることを確認の上、Conventional Commits形式 (`feat:` / `fix:`) でお願いします。

## 📜 License

[MIT](LICENSE)
