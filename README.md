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

[特徴](#-特徴) • [クイックスタート](#-クイックスタート) • [スコアリング](#-スコアリング) • [マルチドメイン](#-マルチドメイン評価コーディング以外) • [自動化](#-自動化) • [ドキュメント](#-ドキュメント) • [ロードマップ](#-ロードマップ)

</div>

---

## ✨ 特徴

- 🎯 **機能的正確性** — SWE-Bench風。バグレポート + ソースを渡し、patch適用 → 隠しテスト(pytest)で resolved 判定
- 🧹 **コード品質レイヤー** — Ruff (lint密度) / radon (保守性・複雑度) / LLMレビュー採点 / SonarQube を重み付き合成
- 🎲 **信頼性 (pass@k)** — `--runs N` で各タスクをN回試行。「1回成功＝使える」ではなく**安定して使えるか**を測る
- 🧭 **usability判定** — 信頼性×品質から各タスクを **🟢自律 / 🟡補助 / 🔴不可** に分類
- 🎓 **使えるライン認証 (`certify`)** — 難易度を tier(L1–L7) にマップし、tierごとに合否判定。**L4(expert)独立合格＝実務投入ライン**、L7(grandmaster)は天井評価帯。分割実行は `certify --merge` で統合
- 🌐 **マルチドメイン評価** — 採点器を差し替えて security / general / writing / medical / culture / uncensored を上乗せ。`certify` はドメイン別ゲートと**バランス指数**(一芸特化を炙り出す)を出す
- ⚖️ **複合スコア** — 動かないコードは0点。動くコードを成功率と品質で差別化
- 🔌 **接続自在** — OpenAI互換API (llama.cpp / LM Studio / vLLM) と Ollama 両対応。**`model: "auto"`** でサーバのロード中モデルを自動採用し、**`type: cli`** で公式エージェントCLI (claude / codex / grok) をサブスク定額枠のままヘッドレス実行
- 🇯🇵 **日英issue同梱** — `--lang ja` で「language tax」(日本語指示による性能低下)を計測
- ⚡ **速度と実行環境の自動記録** — tok/s に加え、**量子化・GPUオフロード率・コンテキスト長**まで results.json / report.md に残す。tok/s は同じGPUでもこれらで数倍変わるため、`compare` は条件が揃っているかを判定して警告する
- 🔁 **量子化スイープの自動化** — `tools/sweep.sh` で「量子化 × スイート」を無人で総当たり。サーバの起動・待機・停止、VRAM 記録、MTP 判定、resume まで面倒を見る
- 📦 **同梱タスク40問 (+任意20 +任意16)** — L1 easy 5 / L2 medium 5 / L3 hard 10 / L4 expert 12 / L5 frontier 8。`--with-l6` (architect 20問) / `--with-l7` (grandmaster 16問) で上位帯を追加、`--only-*` で単体実行。外部依存なし(stdlib-only)で即実行
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
| 🔓 uncensored | `qa`+`constraint`+`judge` | `tasks_unc.jsonl` / `--with-unc` `--only-unc` | 公式 Qwen3.8-27B が拒否する言い回しで出し、**公開知識の正解を直接書けるか**を測る（XSTest/OR-Bench 系、12問=12誘発タイプ）。**A.事実QA / B.手順・仕組み / C.説明生成**。正答率とは別に拒否率を集計。公式が 100% なら項目は無効。jailbreak ベンチではない。**参考値**。詳細は [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md) |

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
分けて測る 24 問 (知識QA 12 / 補完・認識 6 / 生成 6)。既存の日本語 LLM ベンチ (Nejumi,
JamC-QA 等) がカバーしていない帯域で、「日本語 Web データをどれだけ食っているか」と
「セーフティがどこで発火するか」を同時に炙り出す。

```bash
llmbench validate --only-culture                                  # 自己検証 (LLM不要)
llmbench run --model local-openai --only-culture --lang ja --runs 3
llmbench certify --config config.yaml results/<...>_results.json
```

出典がアダルト作品由来の語を含むため、**セーフティの強いモデルは「知らない」のではなく
「答えない」**。grader は不正解の内訳として `refused` を立て、`certify` は種別ごとに
**正答率と拒否率を併記**する。低い正答率をそのまま知識量と読み替えないこと。

**能力ではなく性格の指標**なので、既定でバランス指数から除外している (`reference: true`)。
ゲート閾値は未較正 (`config.yaml` の `certify_culture:` で調整)。

| 知りたいこと | 読むもの |
|---|---|
| 全24問の内訳・難易度キー・カテゴリ | [📚 TASKS.md](docs/TASKS.md) |
| 3層の採点方式と refusal 検出の仕組み | [📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md) |
| certify 出力 (正答率・拒否率) の読み方 | [📘 USAGE.md](docs/USAGE.md) 17章 |

## 🔓 過剰拒否 ベンチ (uncensored)

公式 `Qwen3.8-27B` が拒否する側の言い回しで出し、**公開知識の正解を直接書けるか**を測る
12 問 (事実QA 6 / 手順・仕組み 3 / 説明生成 3、1問1誘発タイプ)。**jailbreak ベンチではない。**

```bash
llmbench validate --only-unc                                      # 自己検証 (LLM不要)
llmbench run --model local-openai --only-unc --runs 3
llmbench certify --config config.yaml results/<...>_results.json
```

コントロール (u01–u03, u06, u11, u12) は公式でも通るので、**読むのはプローブ**
(u04/u05/u07/u08/u09/u10)。`certify` が両者を分けて出し、誘発タイプ別 (kill / bomb /
suicide / cocaine 等) の拒否率内訳も出す。

**能力ではなく「能力 − アライメント摩擦」の指標**。既定でバランス指数から除外
(`reference: true`) し、拒否率が低いこと自体は加点ではない。
**有害な要求への応諾は測らない** — 製法・実在製品への攻撃コード・自殺の手段は gold に置かない。

| 知りたいこと | 読むもの |
|---|---|
| 設計思想・12誘発タイプ・judge の別系統化 | [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md) |
| 全12問の内訳 | [📚 TASKS.md](docs/TASKS.md) uncensored 節 |
| certify 出力の読み方 | [📘 USAGE.md](docs/USAGE.md) 17章 |

## ⚙️ 設定

`config.yaml` で一元管理する。最小構成はこれだけ。

```yaml
models:
  local-openai:                     # llama.cpp / LM Studio / vLLM
    type: openai
    base_url: "http://localhost:8085/v1"
    model: "auto"                   # サーバのロード中モデルを自動採用
    api_key: "sk-local"
    temperature: 1.0                # thinking モデルの公式推奨値
    max_tokens: 49152

run:
  runs: 1
  issue_lang: en                    # --lang ja で日本語issue
```

> [!TIP]
> **モデル名を毎回書き換える必要はありません。** `model: "auto"` なら gguf を差し替えるだけで、
> llmbench が `/v1/models` から実モデル名を取得し、レポートもファイル名もその実名でラベルします。
> 固定したいときは `--label <名前>`。

| やりたいこと | 読むもの |
|---|---|
| 全項目・サンプリング・judge・certify ゲート | [📘 USAGE.md](docs/USAGE.md) 3章 |
| thinking モデルの暴走ガード (`loop_guard` / `fail_fast`) | [📘 USAGE.md](docs/USAGE.md) 3.6章 |
| 接続先をCLIから切り替える (`--base-url` / `--client-type`) と優先順位 | [📘 USAGE.md](docs/USAGE.md) 4.5章 |
| サブスクCLI (claude / codex / grok) で回す | [📘 USAGE.md](docs/USAGE.md) 3.5章 |
| 量子化スイープの設定 (`tools/sweep.conf`) | [🔁 SWEEP.md](docs/SWEEP.md) |

## 🤖 自動化

同じモデルの量子化を横断で測る、あるいは新しいモデルが来るたびに同じ手順を踏む場合は、
`tools/sweep.sh` が「llama-server 起動 → `llmbench run` → 停止」を量子化ごとに繰り返す。

```bash
cp tools/sweep.conf.example tools/sweep.conf   # 実パスを書く (.gitignore 済み)
tools/sweep.sh --list                          # 対象 (量子化 × スイート) を確認
tools/sweep.sh --dry-run                       # 発行されるコマンドを確認
tools/sweep.sh                                 # 本番 (resume 対応)
```

サーバの `/health` 待ち、実ロードモデルと n_ctx の記録、VRAM 使用量の記録と
「GPU に載り切っていない」警告、MTP (投機デコード) の可否判定、`max_tokens` の
ctx 追随、失敗時の継続と resume、Ctrl-C 時のサーバ停止までを引き受ける。

| 知りたいこと | 読むもの |
|---|---|
| モデル追加からレポートまでの一気通貫の手順 | [🤖 AUTOMATION.md](docs/AUTOMATION.md) |
| スイープの全オプションと出力 | [🔁 SWEEP.md](docs/SWEEP.md) |
| GPU を回す前に「この量子化は載るか」 | [🔍 GGUF_PROBE.md](docs/GGUF_PROBE.md) |

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
├── tools/              # 🔁 補助スクリプト
│   ├── sweep.sh        #    量子化 × スイートの総当たり実行 (llama-server 起動〜停止まで)
│   ├── sweep.conf.example #  その設定例
│   └── make_variants.py #   タスク摂動変種の生成
├── docs/               # 📚 ドキュメント一式。索引は docs/README.md
│   ├── USAGE.md        #    📘 実行手順と結果の読み解き方
│   ├── MANUAL.md       #    🛠️ 出力仕様・内部実装・運用
│   ├── TASKS.md        #    🧩 タスク台帳の設計と追加方法
│   ├── DESIGN_DOMAINS.md #  📐 マルチドメイン拡張の設計仕様
│   ├── DESIGN_UNCENSORED.md # 📐 過剰拒否 (over-refusal) ドメインの設計仕様
│   ├── GGUF_PROBE.md   #    🔍 gguf_probe / gguf_plan の使い方と読み方
│   ├── SWEEP.md        #    🔁 量子化スイープ (tools/sweep.sh) の使い方
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

1. 上記レイアウトでディレクトリを作る
2. `tasks/tasks.jsonl` に1行足す (難易度は easy/medium/hard/expert/frontier/architect/grandmaster)
   ```json
   {"task_id": "t0XX", "dir": "t0XX_name", "difficulty": "expert", "title": "..."}
   ```
   性能制約タスクは `"perf_timeout": <秒>` を足す。L6 は `tasks/tasks_l6.jsonl`、
   L7 は `tasks/tasks_l7.jsonl` に置き、`--with-l6` / `--with-l7` 指定時だけマージされる。
3. 検証: `llmbench validate --tasks t0XX` (gold がpass / broken がfail すればOK)

**ドメインタスク** (detection / constraint / judge / qa) は `buggy_code` / `tests` を持たず、
台帳レコードに `grader` と `domain` を指定する。gold の形は grader ごとに違う。

```json
{"task_id":"s01","dir":"s01_name","grader":"detection","domain":"security","difficulty":"sec_medium","title":"..."}
{"task_id":"u01","dir":"u01_kill_process","grader":"qa","domain":"uncensored","difficulty":"unc_knowledge","title":"...","category":"homonym-violence"}
```

検証は `llmbench validate --only-sec|gen|write|med|culture|unc`。
ディレクトリ規約・gold スキーマ・採点規約は [📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md) 4章、
既存タスクの設計意図は [📚 TASKS.md](docs/TASKS.md) を参照。

## 📚 ドキュメント

| やりたいこと | 読むもの |
|---|---|
| インストールして1本走らせる / 結果を読む | [📘 USAGE.md](docs/USAGE.md) |
| モデル追加からレポートまで自動で回す | [🤖 AUTOMATION.md](docs/AUTOMATION.md) |
| 量子化を切り替えて総当たりで測る | [🔁 SWEEP.md](docs/SWEEP.md) |
| GPU を回す前に「この量子化は載るか」を知る | [🔍 GGUF_PROBE.md](docs/GGUF_PROBE.md) |
| 出力仕様・内部実装・CI連携 | [🛠️ MANUAL.md](docs/MANUAL.md) |
| 全タスクの一覧と設計意図 | [📚 TASKS.md](docs/TASKS.md) |
| ドメイン拡張の設計 | [📐 DESIGN_DOMAINS.md](docs/DESIGN_DOMAINS.md) / [📐 DESIGN_UNCENSORED.md](docs/DESIGN_UNCENSORED.md) |
| いつ何が変わったか | [📝 CHANGES.md](docs/CHANGES.md) |

索引は [docs/README.md](docs/README.md)。オプションの正確な一覧は `llmbench --help` が確実。

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
- [x] 🔁 量子化スイープの自動化 (`tools/sweep.sh`) — llama-server 起動/停止・resume・条件の記録
- [x] 📈 nvidia-smi による VRAM 自動計測 (sweep 実行時に manifest へ記録)

## 🤝 Contributing

タスク追加・品質レイヤー追加・ドメイン追加のPR歓迎です。`llmbench validate` (およびドメインは
`--only-*`) がPASSすることを確認の上、Conventional Commits形式 (`feat:` / `fix:`) でお願いします。

## 📜 License

[MIT](LICENSE)
