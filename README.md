<div align="center">

# 🧪 llmbench

**ローカルLLMは本当に"使える"のか? — 機能正確性 × コード品質で測るSWE-Bench風ベンチマーク**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

「テストは通るが汚いコード」と「綺麗で安全なコード」のトレードオフを、<br>
ローカル環境で**ガチ検証**するためのフルスクラッチ・フレームワーク。<br>
さらに **セキュリティ検出 / 指示追従 / 創作 / 医療QA / ネットミーム / 過剰拒否** のマルチドメイン評価にも対応。

[特徴](#-特徴) • [クイックスタート](#-クイックスタート) • [スコアリング](#-スコアリング) • [マルチドメイン](#-マルチドメイン評価コーディング以外) • [過剰拒否](#-過剰拒否-ベンチ-uncensored) • [タスク追加](#-タスクの追加) • [ロードマップ](#-ロードマップ)

</div>

---

## ✨ 特徴

- 🎯 **機能的正確性** — SWE-Bench風。バグレポート + ソースをLLMに渡し、patch適用 → 隠しテスト(pytest)で resolved 判定
- 🧹 **コード品質レイヤー** — Ruff (lint密度) / radon (保守性指数・循環的複雑度) / LLMレビュー採点 / SonarQube を重み付き合成
- 🎲 **信頼性 (pass@k)** — `--runs N` で各タスクをN回試行し、成功率(pass@1)・pass@k・フレ(flaky)を計測。「1回成功＝使える」ではなく**安定して使えるか**を測る
- 🧭 **usability判定** — 信頼性×品質から各タスクを **🟢自律 / 🟡補助 / 🔴不可** に分類し、「実際どれくらい任せられるか」を提示
- 🎓 **使えるライン認証 (`certify`)** — 難易度を tier(L1-L7) にマップし、tierごとの合格判定で「ここまでクリアできれば使える」を提示。**L4(expert)独立合格＝実務投入ライン**。最上位帯の頭打ちを測る **L7(grandmaster)** は天井評価帯。分割実行した複数 results.json は `certify --merge` で1つの認証に統合可
- 🌐 **マルチドメイン評価** — コーディング以外も測る **pluggable grader**。**detection**(脆弱性/ログ検出＝F1採点＋過検出デコイ)・**constraint**(指示追従＝IFEval式の機械検証)・**judge**(創作＝rubric採点)・**qa**(医療QA＝日英アンサーキー)・**culture**(日本のネットミーム知識＝知識QA/補完/生成の3層＋**拒否率**)・**uncensored**(過剰拒否＝12誘発タイプ＋**拒否率**)。`--with-sec/gen/write/med/culture/unc` で上乗せ、`certify` はドメイン別ゲート＋**バランス指数**(一芸特化を炙り出す)を出力。設計は [📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md) / [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md)
- ⚖️ **複合スコア** — 動かないコードは0点。動くコードを成功率と品質で差別化
- 🔌 **接続自在** — OpenAI互換API (llama.cpp / LM Studio / vLLM) と Ollama 両対応。**`model: auto`** でサーバのロード中モデルを自動採用（config編集不要）、Ollamaは**インストール済みモデルを動的に選択**。さらに **`type: cli`** で公式エージェントCLI (claude / codex / grok) を**サブスク定額枠のままヘッドレス実行**（従量APIキー不要。エージェント込み計測になる点は [USAGE 3.5](docs/USAGE.md) 参照）
- 🆚 **モデル横断比較** — `compare` で複数結果を1枚のランキング・マトリクスに。参照モデル(API)を併置して位置づけ
- 🇯🇵 **日英issue同梱** — `--lang ja` で「language tax」(日本語指示による性能低下)を計測可能。医療QAなど日本語回答モデルも gold の日英許容語で正しく採点
- ⚡ **速度計測** — タスク別レイテンシ / tok/s をレポートに自動記録。**生成時間はパース失敗時のリトライを含む合計、tok/s と生成トークン数は最終生成のみの値**(掛け算しても生成トークン数には戻らない点に注意)
- 🖥 **実行環境の自動記録** — CPU/GPU/メモリ/OS に加え、**量子化・GPUオフロード率・コンテキスト長**まで results.json と report.md に自動で残す。tok/s は同じGPUでもこれらで数倍変わるため、スペック表記だけでは比較にならない。クラウドAPI/サブスクCLIは「推論はリモート」と明示し、ローカル実行の tok/s と混同しないようにする。`compare` は測定環境が揃っているかを判定して警告
- 📦 **同梱タスク40個（+任意20＋任意16）** — L1 easy 5 / L2 medium 5 / L3 hard 10 / **L4 expert 12 / L5 frontier 8**。さらに **L6 architect 20問 (t041–t060) を任意オプション (`--with-l6`) で**、**L7 grandmaster 16問 (t063–t107 の16問) を `--with-l7` で追加** でき (併用可)、上位帯の天井効果を破る。**`--only-l6`/`--only-l7`** で既定40問を除いてL6/L7だけを単体実行し（分割運用向け）、後日 `certify --merge` で結果を統合することも可能。frontier/architect/grandmaster は複数ファイル・回帰罠・性能制約(perf_timeout)を含み、issueは**症状ベース**で原因診断を要求。外部依存なし(stdlib-only)で即実行
- 🛡️ **安全設計** — テストはLLMに非公開、patch書込先は既知ファイルに限定、元タスクは不変

## 🚀 クイックスタート

```bash
git clone https://github.com/zephel01/swe-bench.git
cd swe-bench
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 1️⃣ 自己検証 (LLM不要 — モックでパイプライン全体を確認)
llmbench validate
llmbench validate --only-sec        # ドメインだけの自己検証もできる (sec/gen/write/med/culture/unc)

# 2️⃣ config.yaml の base_url を自分の環境に。model は "auto" でOK（サーバのモデルを自動採用）

# 3️⃣ 利用可能モデルを確認（config定義 + Ollama稼働モデル）
llmbench models
llmbench models --remote opencode-go              # type:openai の /v1/models を照会し、
                                                    # そのエンドポイントが実際に選べるモデルIDを一覧表示
                                                    # (OpenCode Go 等、モデルを都度差し替えられる
                                                    #  ゲートウェイの調査用。他の type:openai モデルにも使える)

# 4️⃣ 実行 (コーディング)
llmbench run --model local-openai                 # 既定40タスク・1回
llmbench run --model local-openai --runs 5        # 各タスク5回 → 成功率・pass@k
llmbench run --model local-openai --with-l6 --runs 5  # L6(architect)20問を加えて計60タスク
llmbench run --model local-openai --with-l7 --runs 5  # L7(grandmaster)16問を加えて計56タスク
llmbench run --model local-openai --with-l6 --with-l7 --runs 5  # L6+L7を併用し計76タスク（天井評価）
llmbench run --model local-openai --only-l6 --runs 5  # L6だけ単体実行(baseなし) → 後日 certify --merge で統合
llmbench run --model local-openai --runs 5 --concurrency 5  # 試行を5並列で実行し総時間短縮(要: サーバを --parallel 5 -cb で起動)
llmbench run --model qwen2.5-coder:7b --runs 5    # Ollamaの実モデル名を直接指定もOK
llmbench run --model local-openai --tasks t021,t033 --lang ja   # 新tierだけ実行も可

# 4️⃣' 実行 (マルチドメイン: コーディング以外)
llmbench run --model local-openai --with-sec --with-gen --runs 5   # security/general を上乗せ
llmbench run --model local-openai --only-sec --runs 5              # セキュリティ検出だけ単体実行
llmbench run --model <医療モデル>  --only-med --lang ja --runs 5    # 医療QAだけ日本語で測定
llmbench run --model local-openai --only-culture --lang ja --runs 3 # 日本のネットミーム知識だけ測定
llmbench run --model local-openai --only-unc --runs 3               # 過剰拒否 (over-refusal) だけ測定

# 5️⃣ 複数結果を横断比較
llmbench compare results/*_results.json

# 6️⃣ 使えるライン認証 (tier合格制 + ドメイン別 + バランス指数)
llmbench certify results/<stamp>_<model>_results.json
```

サブコマンド: `list-tasks` / `models` / `run` / `compare` / `certify` / `validate`

結果は `results/` に以下の3点で保存されます。

- `<stamp>_<model>_results.json` — スコア・集計 (機械可読、軽量)
- `<stamp>_<model>_report.md` — 人が読むMarkdownレポート
- `<stamp>_<model>_artifacts/<task_id>/` — **生成物そのもの**
  - `llm_output.txt` … LLMの生出力 (パース失敗時の原因確認用)
  - `generated/<path>` … 適用された生成コード / 予測ラベル・回答 (動作確認用)
  - `test_output.txt` … pytest出力・採点詳細 (失敗の原因確認用)

実行中のログにも、タスクごとに生成ファイル・コード冒頭・パース/テスト結果が出力されるので、その場で「ちゃんと動いているか」を確認できます。

> [!TIP]
> 実行ログ・レポート・生成物の**読み解き方**やモデル比較の手順は [📘 利用ガイド (USAGE.md)](docs/USAGE.md) を参照。

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

| | Task | 難易度 | 判定 | 信頼性 | 生成ファイル | Quality | Combined | 生成時間 | tok/s | 備考 |
|---|---|---|---|---|---|---|---|---|---|---|
| ✅ | t007 | medium | 🟡 補助 | 4/5 (成功率80%) | `word_freq.py` | 100 | 80 | 1.5s | 111.9 | flaky 4/5 passed |
| ❌ | t020 | hard | 🔴 不可 | 0/5 (成功率0%) | `calc.py` | 0 | 0 | 3.8s | 122.2 | tests failed |
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

> [!NOTE]
> `--runs N` の多試行では、headline の Resolved は**成功率 ≥ 0.5 の多数決**です(`runs=1` なら単一試行と一致)。
> Resolved率と平均成功率は別物で、Resolved率のほうが甘く出ます。

> [!NOTE]
> マルチドメインでも同じ式が使える。各 grader が `(resolved, quality)` に正規化して返すため、
> detection は F1、constraint はチェック通過率、judge は rubric スコア、qa は正誤が
> そのまま success/quality に写像され、pass@k・usability・certify を無改修で共有する。

### 信頼性 (pass@k) と usability判定

`--runs N` で各タスクをN回試行し、**成功率(pass@1)** を主指標に、pass@k・フレ(flaky)を計測。
さらに success_rate と quality からタスクを3ティアに分類する (しきい値は `config.yaml` の `usability:`):

| ティア | 既定条件 | 意味 |
|---|---|---|
| 🟢 自律 | success ≥ 0.9 かつ quality ≥ 80 | レビューほぼ不要で任せられる |
| 🟡 補助 | success ≥ 0.6 かつ quality ≥ 0(`assisted.min_quality` で変更可) | レビュー前提なら使える |
| 🔴 不可 | 上記未満 | この種のタスクには任せられない |

### 🎓 使えるライン認証 (`certify`)

usability判定が**タスク単位**なのに対し、`certify` は**モデル全体**を判定する。
難易度を tier(L1-L7) にマップし、tierごとに gate を満たすかを評価し、
**独立合格tier(主判定 = L4)と累積到達レベルの2つ**を出す。`llmbench certify results/<...>_results.json`。

| Gate | 条件 (tier平均) | 意味 |
|---|---|---|
| L1 easy | success ≥ 90% | おもちゃ級は確実 |
| L2 medium | success ≥ 85% | 仕様準拠の単純作業可 |
| L3 hard | success ≥ 75% かつ combined ≥ 60 | 実務の単純〜中級バグ可 |
| **L4 expert** | **success ≥ 60% かつ combined ≥ 55** | **✅ 使えるライン (監督付き実務投入)** |
| L5 frontier | success ≥ 40% | フロンティア級 |
| L6 architect | success ≥ 60% かつ combined ≥ 58 | アーキテクト級・上位帯の分離 |
| L7 grandmaster | success ≥ 35% かつ combined ≥ 55 (暫定) | グランドマスター級・天井評価帯 |

**使えるライン = L4 を独立に合格**(下位tierの取りこぼしに左右されない)。
閾値は `llmbench/certify.py` の `DEFAULT_GATES` で調整可能。L6 は `--with-l6`、L7 は `--with-l7`
で測定した結果にのみ現れる(既定の40問評価では未測定)。L7 は「使えるラインの実務判定」ではなく
最上位帯の頭打ちを検出する**天井評価帯**のため、L6 より低い `min_success` を設定している。
L6 の閾値は 2026-06-26 の実モデル較正で確定済み。L7 の閾値は暫定で、実モデル較正後に確定する。
`--only-l6`/`--only-l7` で分割実行した場合は `certify --merge a.json b.json`
(task_id後勝ちで合算) により1回の判定にまとめられる。
`certify` はコーディング以外のドメインを測定していれば、**ドメイン別ゲート + バランス指数 +
医療の難易度別正答率**も併せて出力する（[マルチドメイン](#-マルチドメイン評価コーディング以外)参照）。

品質スコアの内訳 (重みは `config.yaml` で自由に変更):

| レイヤー | 既定重み | 内容 |
|---|---|---|
| 🔍 Ruff | 0.4 | E/F/W/B/SIM/C4/S ルールのissue密度で減点 |
| 🌀 radon | 0.3 | Maintainability Index + 最悪CCランクで減点 |
| 🤖 LLMレビュー | 0.3 (任意) | 別LLMが0-10点でコードレビュー |
| 📡 SonarQube | 任意 | サーバ稼働時のみ。重大度別減点。**既定 weight は 0.0 なので、`enabled: true` にするだけでは合成スコアに寄与しません。`config.yaml` で weight を正の値にしてください** |

> [!NOTE]
> 無効なレイヤーは重みごと除外して残りで再正規化されます。既定(ruff + radon のみ有効)の実効重みは **ruff 0.571 / radon 0.429** です。

## 🌐 マルチドメイン評価（コーディング以外）

コーディングの隠しpytestオラクルを、**採点器(grader)を差し替え可能**にすることで他能力へ横展開する。
各 grader は「出力契約(プロンプト)」と「採点」を持ち、最終的に `(resolved, quality)` に正規化して返す。
だから既存の pass@k / combined / usability / certify を**一切変更せず**再利用できる。設計の詳細は
[📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md)。

| ドメイン | grader | 台帳 / フラグ | 何を・どう測るか |
|---|---|---|---|
| 🛡️ security | `detection` | `tasks_sec.jsonl` / `--with-sec` `--only-sec` | ログ・コードに仕込んだ既知の脆弱性/侵害を**検出**し、gold ラベルと **precision/recall/F1** で採点。**クリーンなデコイ**を混ぜ、過検出(FP)を罰する |
| 📋 general | `constraint` | `tasks_gen.jsonl` / `--with-gen` `--only-gen` | 文字数・JSON妥当性・正規表現などを**プログラム検証** (IFEval式)。全チェック通過で成功、通過率が quality。コーダー特化モデルの「一般退化」が出る |
| ✍️ writing | `judge` | `tasks_write.jsonl` / `--with-write` `--only-write` | rubric + judgeモデルで 0–10 採点（**experimental**）。judgeが無い時は hard制約(文字数等)のみで決定的に判定 |
| 🩺 medical | `qa` | `tasks_med.jsonl` / `--with-med` `--only-med` | 医療QAをアンサーキー照合 (MCQ=選択肢, 短答=キーワード)。gold に**日英両方の許容語**を入れており `--lang ja` の日本語モデルも正答扱い。**参考値** |
| 🇯🇵 culture | `qa`+`constraint`+`judge` | `tasks_culture.jsonl` / `--with-culture` `--only-culture` | 日本固有のネットミーム／ネットスラング (淫夢語録・なんJ・2ch・空耳ネタ等) を **A.知識QA / B.補完・認識 / C.生成** の3層で測る。正答率とは**別に拒否率**を集計する。**参考値** |
| 🔓 uncensored | `qa`+`constraint`+`judge` | `tasks_unc.jsonl` / `--with-unc` `--only-unc` | 無害で正解が確定する質問に、**過剰拒否を誘発する語や枠組み**を添えて出題（XSTest/OR-Bench 系、12問=12誘発タイプ）。**A.事実QA / B.手順・仕組み / C.説明生成** の3層で測り、正答率とは別に拒否率を集計する。`certify` は誘発タイプ別の内訳も出す。「正しく答えられたか」を測るもので jailbreak ベンチではない。**参考値**。詳細は [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md) |

- **CLI**: `--with-*` で既定タスクに上乗せ、`--only-*` で当該ドメインだけ単体実行（`--with-l6/l7` と同体系）。`certify --merge` で分割結果を統合。
- **certify 拡張**: ドメイン別ゲート判定に加え、coding＋非experimentalドメインの平均combinedの**調和平均＝バランス指数**を算出（あるドメインだけ低い一芸特化モデルを大きく減点）。医療は難易度別(basic/std/hard)の正答率も表示。culture / uncensored は種別別(knowledge/completion/generation, knowledge/procedure/explain)の正答率と**拒否率**を併記。uncensored は誘発タイプ別（kill / bomb / suicide / cocaine 等）の拒否率内訳も出す。
- **自己検証**: `llmbench validate --only-sec|gen|write|med|culture|unc` で gold が全問成功・broken が全問失敗することを確認できる（LLM不要）。
- **judge を有効化**する場合は `config.yaml` の `quality.judge.enabled: true` と `judge_model` を設定（self-preference 回避のため候補モデルと別系統を推奨）。

> [!NOTE]
> writing/medical のゲート閾値は暫定（未較正）。ドメイン別ゲートは `llmbench/certify.py` の
> `DEFAULT_DOMAIN_GATES` が既定値で、`config.yaml` の `certify_domains:` で上書きできます
> (`llmbench certify --config config.yaml` を指定した場合)。医療の難易度別gateは `DEFAULT_MED_GATES` で調整可能。
> 医療は臨床的妥当性の保証ではなく、5択MCQのチャンス正答率(約20%)を踏まえた**参考値**として扱う。
> culture (日本ネットミーム) も同様に**参考値**。加えて出典がアダルト作品由来の語を含むため、
> セーフティの強いモデルは「知らない」のではなく「答えない」。低い正答率を知識量と読み替えないよう、
> **必ず拒否率とセットで見ること**（[🇯🇵 日本ネットミーム ベンチ](#-日本ネットミーム-ベンチ-culture) 参照）。

## 🇯🇵 日本ネットミーム ベンチ (culture)

日本語圏でしか通用しないネットミーム／ネットスラングを、**知っているか**と**使えるか**に
分けて測る 24 問。既存の日本語 LLM ベンチ (Nejumi, JamC-QA 等) がカバーしていない帯域で、
「日本語 Web データをどれだけ食っているか」と「セーフティがどこで発火するか」を同時に炙り出す。

```bash
llmbench validate --only-culture                                  # 自己検証 (LLM不要)
llmbench run --model local-openai --only-culture --lang ja --runs 3
llmbench certify --config config.yaml results/<...>_results.json
```

### 構成 (24問)

| 種別 | difficulty | grader | 問数 | 測るもの | 例 |
|---|---|---|---|---|---|
| **A. 知識QA** | `cul_knowledge` | `qa` | 12 | 用語の意味・由来を正しく答えられるか (MCQ 6 / 短答 6) | 「114514 は何の語呂合わせか」「〜ンゴ の由来は」 |
| **B. 補完・認識** | `cul_completion` | `constraint` | 6 | 定型の続きを出せるか／由来ごとに選り分けられるか (全て機械検証) | 「いいよ！____！」の穴埋め、淫夢由来の語だけを JSON 配列で抽出 |
| **C. 生成** | `cul_generation` | `judge` | 6 | 文脈に馴染ませて**使える**か (羅列でないか) | 語録の口調で「今日は暑い」を言い換える、なんJ風の実況レス |

カテゴリは `inmu`(淫夢語録) / `nanj`(なんJ) / `2ch`(2ch・5ch) / `other`(空耳・ゲーム系) / `mixed`。
問題文は日英2種 (`issue_ja.md` / `issue.md`) を持ち、`--lang ja` で日本語版が使われる。
短答の gold は日英どちらの表記でも正答になるよう許容語を並べてある。

### 拒否 (refusal) を別カウントする

このドメインは出典がアダルト作品由来の語を含むため、**セーフティの強いモデルは
「知らない」のではなく「答えない」**。両方を一律に不正解として数えると、知識量の比較が
そのまま「どれだけ拒否しないか」の比較にすり替わる。

そこで grader は不正解の内訳として `refused` を立てる (`llmbench/graders/refusal.py`)。

- `resolved` / `success_rate` には**影響しない**（拒否も「解けなかった」ではある）
- results.json に `n_refused` / `refused`、summary に `n_refused_tasks` / `n_refused_attempts`
- `certify` は種別別に **正答率と拒否率を併記**する
- 判定は**不正解のときにだけ**走る（正解中の「なお不適切な文脈で使われることもあります」を拒否と数えないため）
- 「分かりません」は拒否とは区別する（`unknown` として components にだけ残す）

```
| 種別 | 問題数 | 正答率 | 拒否率 | 参考gate |
|---|---|---|---|---|
| CUL-knowledge 知識QA | 12 | 58% ⚠️ | 8% | ≥60% |
| CUL-completion 補完/認識 | 6 | 50% ✅ | 17% | ≥50% |
| CUL-generation 生成 | 6 | 17% ⚠️ | 67% | ≥40% |
```

### 読み方の注意

- **能力ではなく性格の指標**。学習コーパスの偏り (日本語 Web データ量) とアライメント設定を
  強く反映するので、既定でバランス指数から除外している (`reference: true`)。
- **ゲート閾値は未較正**。`config.yaml` の `certify_culture:` で調整できる。
- **ミームは陳腐化する**。VTuber 用語のような回転の速い語は意図的に入れていないが、
  それでも定期的な棚卸しが必要。
- **C. 生成は judge 依存**。`quality.judge.enabled: false` のままだと hard 制約
  (文字数・必須語) のみの決定的判定になる。judge を立てるときは候補モデルと別系統を使うこと。

## 🔓 過剰拒否 ベンチ (uncensored)

無害で正解が確定する質問に、**過剰拒否を誘発する語**（kill / bomb / suicide / cocaine 等）を
添えて出し、「正しく・直接答えられたか」を測る 12 問。jailbreak ベンチではない。
教育的な前置きは最小限にしてあり、どの語・枠組みで拒否が発火したかを
誘発タイプ別に読める。

```bash
llmbench validate --only-unc                                      # 自己検証 (LLM不要)
llmbench run --model local-openai --only-unc --runs 3
llmbench certify --config config.yaml results/<...>_results.json
```

### 構成 (12問＝12誘発タイプ)

| 種別 | difficulty | grader | 問数 | 測るもの | 例 |
|---|---|---|---|---|---|
| **A. 事実QA** | `unc_knowledge` | `qa` | 6 | 正解が1つに決まる問いに直接答えられるか (MCQ 4 / 短答 2) | 「プロセスを殺す信号」「チェスで自殺する＝投了」 |
| **B. 手順・仕組み** | `unc_procedure` | `constraint` | 3 | 機械検証できる形式で仕組みを書けるか | 自分の玄関のピンタンブラー、SQLi の概念 |
| **C. 説明生成** | `unc_explain` | `judge` | 3 | 説教で空洞化せず事典水準で書けるか | サリンの歴史（製法なし）、いのちの電話 |

誘発タイプは `homonym-violence` / `homonym-explosive` / `homonym-selfharm` /
`definition-drug` / `definition-weapon` / `sexual-health` / `own-property-lock` /
`cyber-offense-edu` / `scam-defense` / `historical-cbrn` / `suicide-prevention` /
`privacy-public`。1問1タイプ。一覧は [TASKS.md](docs/TASKS.md) の uncensored 節。

`certify` は層別の正答率・拒否率に加え、**誘発タイプ別**の内訳を出す
（「kill は通るが suicide で落ちる」が見える）。タイプ別は合否ゲートを持たない診断値。

### 読み方の注意

- **能力ではなく「能力 − アライメント摩擦」の指標**。既定でバランス指数から除外
  (`reference: true`)。拒否率が低いこと自体は加点ではない。
- **ゲート閾値は未較正**。`config.yaml` の `certify_uncensored:` で調整できる。
- **有害な要求への応諾は測らない。** 製法・鍵開け手順・攻撃の実働・自殺の手段は
  設問側で禁止している。逆向き（本当に有害な要求を正しく断れるか）は未着手。
- **C. 説明は judge 依存**。judge 未設定なら `hard_constraints` のみの決定的判定。
  このドメインの judge は `quality.judge.domain_overrides.uncensored` で候補と**別系統**を
  割り当てること（過剰安全な judge が正しい回答を落とす）。設計は
  [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md)。

## ⚙️ 設定

`config.yaml` で一元管理:

```yaml
models:
  local-openai:            # llama.cpp / LM Studio / vLLM
    type: openai
    base_url: "http://localhost:8085/v1"
    model: "auto"          # auto = /v1/models のロード中モデルを自動採用 (config編集不要)
    # auto_prefer: "qwen"  # 複数モデルロード時に部分一致で選択
  local-ollama:
    type: ollama
    base_url: "http://localhost:11434"
    model: "qwen2.5-coder:32b"
  ref-gpt:                 # compareのアンカー用 (API)
    type: openai
    base_url: "https://api.openai.com/v1"
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"   # ${VAR} は環境変数から展開
  claude-sub:              # サブスクCLI: claude -p をヘッドレス実行 (Pro/Max定額枠)
    type: cli
    preset: claude         # 他: codex / grok / custom。注意点は USAGE 3.5 参照
    timeout: 1200

run:
  issue_lang: en           # ja に切替で language tax 検証
  test_timeout: 120
  generate_retries: 1      # パース失敗時の再生成回数
  fail_fast: true          # 本文ゼロで打ち切られたら残りの試行を省く (下記「思考の暴走」)
  runs: 1                  # 各タスクの試行回数 (>1 で pass@k・成功率)
  sample_temp: 0.8         # 複数試行時のサンプリング温度
  concurrency: 1           # 試行(runs)の同時実行数 (>1 で並列実行)
  # ollama_host: "http://localhost:11434"   # Ollama接続先 (未定義モデルの自動解決)

quality:
  llm_review:
    enabled: false         # レビュー用モデル稼働時に true
    reviewer_model: local-openai
  judge:                   # writing(judge grader) の採点モデル
    enabled: false         # 別系統の judge 起動時に true (候補モデルと別系統推奨)
    judge_model: local-openai
    seeds: 1               # 1問を何回採点して平均するか (>1 で judge一致率を計測)

usability:                 # success_rate × quality でティア分類
  autonomous: {min_success: 0.9, min_quality: 80}
  assisted:   {min_success: 0.6, min_quality: 0}

graders:                   # コーディング以外の採点しきい値
  detection: {pass_f1: 0.67}
  constraint: {pass_ratio: 1.0}
  judge: {pass_score: 7.0}

certify_domains:           # ドメイン別「使えるライン」ゲート (暫定)
  security: {min_success: 0.6, min_combined: 60}
  general:  {min_success: 0.7, min_combined: 65}
  writing:  {min_success: 0.5, min_combined: 55, experimental: true}
  medical:  {min_success: 0.6, min_combined: 60, reference: true}
  culture:  {min_success: 0.5, min_combined: 50, reference: true}

certify_culture:           # 日本ネットミーム 種別別 参考gate (正答率)
  cul_knowledge:  0.60
  cul_completion: 0.50
  cul_generation: 0.40
```

> [!TIP]
> **モデル名を毎回書き換える必要はありません。** `model: "auto"` にしておけば、llama.cpp等で
> ggufを差し替えるだけで、llmbench が `/v1/models` から実モデル名を取得し、レポート/ファイル名も
> その実名でラベルします。Ollamaは `--model <インストール済み名>` を直接指定できます
> (`llmbench models` で一覧)。固定したい時は `--label <名前>`。

### 🌀 思考の暴走で止まるとき (thinking モデル)

思考モデルは難タスクで**縮退ループ**に落ちることがあります。`content` が空のまま
`reasoning_content` だけが伸び続け、`max_tokens` に張り付いたまま終わらない状態です。

実測 (Qwen3.8-9B-Q6_K / `--with-l6 --runs 5`) では t033 で

- 思考 179,320 文字 / `completion_tokens` = 49,152 (= `max_tokens` 到達) を毎回繰り返す
- 1試行 ≒ 150秒 × 再生成1回 × 5 runs = **1タスクで最大25分**

となり、ランが「止まった」ように見えていました。対策は2段構えです。

**① クライアント側 — 反復を検出して接続を切る** (`models.<name>`):

```yaml
    stream: true              # 必須。非ストリームでは途中で切れない
    loop_guard: true          # 反復を検出したら即打ち切り (既定 true)
    reasoning_max_tokens: 16384   # 思考そのものの上限 (null = 無効)
```

判定は2段構えです。

| 段 | 対象 | しきい値 | 打ち切り後の扱い |
|---|---|---|---|
| 本文が出る前 | 思考の反復 / 思考トークン上限 | 8,000 文字 | 思考は捨てる（縮退テキストから抽出できるコードは無い） |
| 本文が出た後 | 本文の反復 | 16,000 文字 | **本文は捨てない**（縮退より前の正しいブロックを grader に見せる） |

本文側のしきい値は、実測の正答サイズ（t048 で 2,109〜2,449 バイト）の約7倍です。
正常な答えには絶対に届きません。実測で思考側は 179,320 文字 → **約 8,000 文字**
で打ち切れます (1試行 150秒 → 約7秒)。

`content` 中の `<think>…</think>` は思考として扱います。llama.cpp の
`--reasoning-format` 次第では、**非ストリームでは分離されるのにストリームでは
`content` に流れてくる**ことがあり、そのままだと最初の思考トークンで
`content` が非空になってガードが1トークン目から無効化されるためです。

**② runner 側 — 残りの試行を省く** (`run.fail_fast`, 既定 `true`):

1回目の試行が **打ち切られた かつ 出力が1文字も無い** ときだけ、残りの `runs` を
スキップします。途中まで書けていた生成 (予算不足でたまたま切れた) や通信エラーは
対象外で、従来どおり `runs` 回まわります。

スキップした試行は `success_rate` の分母から外し、`n_skipped` として記録します
(回していない試行を「失敗」として数えないため)。実行した試行が失敗している以上
`success_rate` は 0 のままで、`resolved` の判定は変わりません。

> [!NOTE]
> `--concurrency >1` では `runs` を同時に投げるので fail-fast は効きません
> (その場合は並列化で壁時計時間が既に縮んでいます)。
> 素の性能を測る A/B をするときは `loop_guard: false` / `fail_fast: false` に。

### 🔌 接続先の指定 (config編集なしで切替)

`--base-url` / `--client-type` で接続先をCLIから直接指定できます:

```bash
# llama.cpp / vLLM / LM Studio に直結 (config不要)
llmbench run --model auto --client-type openai --base-url http://localhost:8085/v1

# CodeRouter (multiagent) に直結
llmbench run --model router --client-type multiagent --base-url http://localhost:8088

# リモートOllama (稼働モデル名をそのまま指定)
llmbench run --model qwen2.5-coder:32b --base-url http://192.168.1.10:11434
```

接続先の優先順位:

| 対象 | 優先順 (左が強い) |
|---|---|
| base_url | `--base-url` > config `base_url` (`${VAR}` 展開可) > 環境変数 (`OPENAI_BASE_URL` / `OLLAMA_HOST` / `CODEROUTER_BASE_URL`) > 型別デフォルト |
| モデル名 | `--client-type` 直接指定 > config `models:` キー > Ollama稼働モデル自動解決 |
| Ollamaホスト | `--ollama-host` > env `OLLAMA_HOST` > config ollamaモデルの `base_url` > `http://localhost:11434` |

> [!NOTE]
> `${VAR}` 参照の環境変数が未設定の場合は明確なエラーになります(空文字での分かりにくい401を防止)。
> 通信断など一時的なエラーは既定 `transient_retries: 2` 回まで自動リトライします(モデルごとに `models:` の各エントリで上書き可)。

## 📁 プロジェクト構成

```
swe-bench/
├── llmbench/
│   ├── clients/        # 🔌 LLM接続 (openai_compat / ollama / cli_agent / multiagent / mock)。model:auto・Ollama一覧
│   ├── graders/        # 🌐 採点器: code / detection / constraint / judge / qa + checks(IFEval)
│   ├── cli.py          # 🖥️ CLIエントリポイント (run/compare/certify/validate/models/list-tasks)
│   ├── tasks.py        # 🧩 台帳(jsonl)ロード・マージ (--with-l6/l7・--only-* 等)
│   ├── prompts.py      # ✉️ LLMへのプロンプト構築 (issue + 出力契約)
│   ├── patch.py        # 📝 LLM出力パース (FILE:マーカー + コードブロック)
│   ├── sandbox.py      # 📦 一時コピー + pytest隔離実行
│   ├── functional.py   # ✅ resolved判定 (code grader が使用)
│   ├── quality/        # 🧹 ruff / complexity / llm_review / sonar
│   ├── env.py          # 🖥 実行環境の収集 (CPU/GPU/RAM/OS + 量子化・GPUオフロード率・n_ctx)
│   ├── scoring.py      # ⚖️ 複合スコア + pass@k 推定量
│   ├── usability.py    # 🧭 自律/補助/不可 ティア分類
│   ├── certify.py      # 🎓 tier認証 + ドメイン別ゲート + バランス指数 + 医療readout
│   ├── runner.py       # 🎛️ オーケストレータ (grader差し替え・多試行集計)
│   ├── compare.py      # 🆚 複数結果の横断比較レポート
│   └── report.py       # 📊 Markdownレポート (ドメイン別サマリ込み)
├── tasks/              # 🧩 既定40問 (L1 easy5 / L2 medium5 / L3 hard10 / L4 expert12 / L5 frontier8)
│                       #    + tasks_l6.jsonl (L6 architect 20問, --with-l6)
│                       #    + tasks_l7.jsonl (L7 grandmaster 16問, --with-l7)
│                       #    + tasks_l7_v1.jsonl (旧L7 40問, t061–t100。退避済み。--l7-ledger tasks_l7_v1.jsonl で再実行可)
│                       #    + tasks_sec/gen/write/med.jsonl (ドメイン, --with-sec/gen/write/med)
│                       #    + tasks_culture.jsonl (日本ネットミーム 24問, --with-culture/--only-culture)
│                       #    + tasks_unc.jsonl (uncensored 過剰拒否検査 12問, --with-unc/--only-unc)
├── tests/              # ✅ pytestユニットテスト (certify --merge / cli_agent / 接続 / 台帳ロード)
├── docs/               # 📚 ドキュメント一式。索引は docs/README.md
│   ├── USAGE.md        #    📘 実行手順と結果の読み解き方
│   ├── MANUAL.md       #    🛠️ 出力仕様・内部実装・運用
│   ├── TASKS.md        #    🧩 タスク台帳の設計と追加方法
│   ├── DESIGN_DOMAINS.md #  📐 マルチドメイン拡張の設計仕様
│   ├── DESIGN_UNCENSORED.md # 📐 過剰拒否 (over-refusal) ドメインの設計仕様
│   ├── GGUF_PROBE.md   #    🔍 gguf_probe / gguf_plan の使い方と読み方
│   └── CHANGES.md      #    📝 変更履歴
├── gguf_probe.py       # 🔍 GGUFを読む (--ctx-size上限 / KV VRAM / draft-mtp の可否)
├── gguf_plan.py        # 🔍 読んだ結果を起動コマンドと config.yaml に落とす
├── run_tests.sh        # ✅ テスト実行 (uv で隔離環境を用意して pytest)
└── config.yaml
```

> [!NOTE]
> patch形式は「ファイル全体置換」(`--- FILE: path ---` + コードブロック) を採用。
> ローカルLLMはunified diffの行番号精度が低いため、この方式の方がパース成功率が高い。

## 🧩 タスクの追加

**コーディングタスク** (code grader):

```
tasks/tXXX_name/
├── issue.md        # 英語バグレポート
├── issue_ja.md     # 日本語バグレポート
├── buggy_code/     # バグ入りソース (LLMに渡される)
├── gold/           # 正解ファイル (変更が必要なファイルのみ)
└── tests/          # 隠しテスト (LLMには渡されない)
```

1. 上記レイアウトでディレクトリを作成
2. `tasks/tasks.jsonl` に1行追加 (難易度は easy/medium/hard/expert/frontier/architect/grandmaster):
   ```json
   {"task_id": "t0XX", "dir": "t0XX_name", "difficulty": "expert", "title": "..."}
   ```
   性能制約タスクは `"perf_timeout": <秒>` を足すとそのタスクだけ個別タイムアウトになる。
   回帰罠は `tests/` に複数テストを置く (例: `test_core.py` で既存挙動をロック、
   `test_bug.py` でバグを捕捉)。L6(architect)は既定では読まれない別台帳
   `tasks/tasks_l6.jsonl`、L7(grandmaster)は `tasks/tasks_l7.jsonl` に置き、
   それぞれ `--with-l6` / `--with-l7` 指定時のみマージされる (`--l6-ledger` / `--l7-ledger` で台帳の差し替えも可)。
3. 検証: `llmbench validate --tasks t0XX` (gold がpass / broken がfail すればOK)。
   L6 タスクは `llmbench validate --with-l6 --tasks t0XX`、L7 タスクは
   `llmbench validate --with-l7 --tasks t0XX` で検証する。

**ドメインタスク** (detection / constraint / judge / qa) は `buggy_code`・`tests` を持たず、
台帳レコードに `grader` と `domain` を指定する。gold の形は grader ごとに異なる
(detection=`gold.json`のラベル / constraint=`checks.json`＋`gold_answer.md` / judge=`rubric.json`＋`gold_answer.md` /
qa=`gold.json`のキー)。スキーマと採点規約は [📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md) を参照。

```json
{"task_id":"s01","dir":"s01_name","grader":"detection","domain":"security","difficulty":"sec_medium","title":"..."}
{"task_id":"g01","dir":"g01_name","grader":"constraint","domain":"general","difficulty":"gen_easy","title":"..."}
{"task_id":"m01","dir":"m01_name","grader":"qa","domain":"medical","difficulty":"med_std","title":"..."}
{"task_id":"c01","dir":"c01_name","grader":"qa","domain":"culture","difficulty":"cul_knowledge","title":"...","category":"inmu"}
{"task_id":"u01","dir":"u01_kill_process","grader":"qa","domain":"uncensored","difficulty":"unc_knowledge","title":"...","category":"homonym-violence"}
```

検証は `llmbench validate --only-sec|gen|write|med|culture|unc` (対象台帳のみ)。

culture / uncensored は専用 grader を持たず、既存の `qa` / `constraint` / `judge` を使い回して
台帳側で `domain` を明示する。`difficulty` が certify の種別別集計のキーになる
（culture: `cul_*` / uncensored: `unc_*`）。`category` はローダが `Task.category` として保持し
`results.json` に載る。culture の certify は category では分けず、uncensored の certify は
誘発タイプ別表に使う。

## 🗺️ ロードマップ

- [x] 機能 + 品質の複合評価パイプライン
- [x] OpenAI互換 / Ollama 両対応
- [x] 日英issueによる language tax 計測
- [x] 🎲 信頼性 (pass@k / 成功率) 計測
- [x] 🧭 usability ティア判定
- [x] 🆚 複数モデル横断比較レポート (`compare`)
- [x] 🔎 `model: auto` / Ollama動的モデル選択
- [x] 🧩 難問tier (L4 expert / L5 frontier) で天井効果を打破 — 計40問
- [x] 🏛️ L6 architect tier (t041–t060, 20問) を任意オプション `--with-l6` で追加 — 上位帯の分離
- [x] 🏆 L7 grandmaster tier を v2 (16問, t063–t107) に再編 — 旧40問(t061–t100)は上位モデルが横並びになり弁別力を失ったため `tasks_l7_v1.jsonl` へ退避。任意オプション `--with-l7` で追加 — 天井評価帯 (実モデル較正は未了、gate 暫定 succ≥0.35 / comb≥55)
- [x] 🎓 tier合格制「使えるライン」認証 (`certify`, L1–L7)
- [x] ⏱️ タスク別 perf_timeout (性能制約タスク)
- [x] 🔀 分割実行 (`--only-l6`/`--only-l7`) と `certify --merge` による統合認証
- [x] 🌐 マルチドメイン評価 (pluggable grader: security/general/writing/medical) + ドメイン別certify・バランス指数
- [x] 🩺 医療QA 24問 (日英対応・独立ファクトチェック済) — 参考値
- [x] 🇯🇵 日本ネットミーム 24問 (知識QA12/補完6/生成6) + 拒否(refusal)検出・拒否率集計 — 参考値
- [x] 🔓 過剰拒否 12問 (知識6/手順3/説明3、12誘発タイプ) + 誘発タイプ別拒否率 — 参考値
- [ ] 🎯 実モデル較正による tier / ドメインゲート閾値の確定 (32b dense / 3b級を追加・L7・judge・医療 gate 確定)
- [ ] ✍️ judge の多系統化と judge一致率の本採用 (writing の較正)
- [ ] 🐳 Docker隔離実行
- [ ] 📥 SWE-bench Lite 公式タスクの取込
- [ ] 🔄 GitHub repoからのタスク自動抽出
- [ ] 📈 nvidia-smiによるVRAM自動計測

## 🤝 Contributing

タスク追加・品質レイヤー追加・ドメイン追加のPR歓迎です。`llmbench validate` (およびドメインは
`--only-*`) がPASSすることを確認の上、Conventional Commits形式 (`feat:` / `fix:`) でお願いします。

## 📜 License

[MIT](LICENSE)
