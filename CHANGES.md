# 🆕 マルチドメイン評価 — security / general / writing / medical (pluggable grader)

コーディング専用だった評価を、**採点器(grader)を差し替え可能**にして他能力へ横展開しました。
各 grader は「出力契約(プロンプト)」と「採点」を持ち、最終的に `(resolved, quality)` に
正規化して返すため、既存の pass@k / combined / usability / certify は**無改修**で共有されます。
**既定の挙動・既存スコアは不変**（`grader` 未指定は `code`、既定台帳のみの実行は結果一致）。

| ドメイン | grader | 台帳 / フラグ | 採点 |
|---|---|---|---|
| 🛡️ security | detection | tasks_sec.jsonl / `--with-sec` `--only-sec` | 脆弱性/侵害の検出を precision/recall/F1。**クリーンなデコイ**で過検出(FP)を罰する |
| 📋 general | constraint | tasks_gen.jsonl / `--with-gen` `--only-gen` | 指示追従を IFEval式に機械検証(文字数/JSON/正規表現…)。全通過で成功、通過率が quality |
| ✍️ writing | judge | tasks_write.jsonl / `--with-write` `--only-write` | rubric+judgeで0–10採点(experimental)。judge無しは hard制約のみで決定的判定 |
| 🩺 medical | qa | tasks_med.jsonl / `--with-med` `--only-med` | 医療QAをアンサーキー照合。gold に**日英許容語**→ `--lang ja` のJPモデルも正答扱い(参考値) |

| 追加/変更 | 内容 |
|---|---|
| 🌐 `llmbench/graders/` | base/registry + `checks.py`(IFEval) + `code`/`detection`/`constraint`/`judge`/`qa` |
| 🚩 CLI | `--with-sec/gen/write/med` と `--only-*`(`--with-l6/l7` と同体系)。`_ledgers()` を拡張 |
| 🎓 `certify` | ドメイン別ゲート + **バランス指数**(coding＋非experimentalの調和平均で一芸特化を減点) + 医療の難易度別正答率(basic/std/hard) |
| ⚙️ config | `graders:`(pass_f1 / pass_ratio / pass_score)・`quality.judge:`・`certify_domains:` |
| 📊 report | ドメイン別サマリ節を追加 |
| 🩺 医療QA 24問 | 薬理/循環器/救急/内分泌/感染/腎/神経/小児/産婦/中毒。**独立エージェントでファクトチェック済**。MCQ＋短答、難易度 basic/std/hard、日英許容語で JP 医療モデルも測定可 |
| 📐 仕様書 | `DESIGN_DOMAINS.md`(pluggable grader の設計・各スキーマ・採点規約) |

**検証**: `llmbench validate --only-sec|gen|write|med` が全て PASS(gold全成功・broken全失敗)。
grader 判別テスト(正答→高スコア / 曖昧→0 / デコイ過検出→precision0で失格 / 4個の箇条書き→75点)、
および日本語回答(「アドレナリンを筋注」「くも膜下出血」等)が正答・誤答が失格することを確認。

> 注: writing/medical のゲート閾値は暫定(未較正)。医療は臨床的妥当性の保証ではなく
> 参考値(5択MCQのチャンス正答率≈20%)。判定は `certify.py` の `DEFAULT_DOMAIN_GATES` /
> `DEFAULT_MED_GATES`、`config.yaml` の `graders:` / `certify_domains:` で調整可能。

---

# 🆕 分割実行対応 — `--only-l6` / `--only-l7` と `certify --merge`

L6/L7 を含めた全問実行は時間がかかるため、**先に既定40問だけ実行し、後日 L6/L7 だけを
追加実行して、最後に統合認証する分割運用**に対応しました。**既定の挙動・既存
`--with-l6`/`--with-l7` は不変**です。`--only-l6`/`--only-l7` を付けたときだけ、既定台帳
`tasks.jsonl` を除外して指定tierだけを実行します（list-tasks / run / validate 共通）。

| 指定 | 対象問題 | 問題数 |
|---|---|---|
| なし | 既定40問 | 40 |
| `--with-l6` | 既定40問 + L6 20問 | 60 |
| `--with-l7` | 既定40問 + L7 40問 | 80 |
| `--with-l6 --with-l7` | 既定40問 + L6 20問 + L7 40問 | 100 |
| `--only-l6` | L6 20問のみ（baseなし） | 20 |
| `--only-l7` | L7 40問のみ（baseなし） | 40 |
| `--only-l6 --only-l7` | L6 20問 + L7 40問（baseなし） | 60 |
| `--only-l6 --with-l7` | L6 20問 + L7 40問（onlyが1つでもあればbase除外・最終集合はonly/withの和集合） | 60 |
| `--only-l6 --with-l6` | L6 20問（二重追加なし） | 20 |

| 追加 | 内容 |
|---|---|
| 🔀 `--only-l6` / `--only-l7` | list-tasks / run / validate 共通の `_common_args` に追加。既定台帳 `tasks.jsonl` を除外し、指定tierの台帳だけを対象にする。`--with-l6`/`--with-l7`・`--l6-ledger`/`--l7-ledger` はそのまま併用可 |
| 🔗 `certify --merge` | 複数 `results.json` の `results` 配列を合算して1つのtier認証を出す。`llmbench certify --merge a.json b.json` / llmbench非依存の単体スクリプト `python3 certify.py --merge a.json b.json` の両方に対応 |
| 🧮 `merge_results()` | task_id 重複は**後勝ち**（後に指定したファイルを優先。再測定結果で上書きする意図）。モデル名は各ファイルの `model` を出現順distinctで `" + "` 連結（同一なら1つ）。`--runs` 数が異なる結果同士の合算も可（タスク単位のsuccess_rate平均で集計するため破綻はしないが、tier内で試行数が不均一になる点は注意） |

**推奨フロー**: `llmbench run`（既定40問）→ 後日 `llmbench run --only-l6`（L6の20問だけ）
→ `llmbench certify --merge base.json l6.json` で L1〜L6 の統合認証を1回で出す。

**検証**: `list-tasks --only-l6`=20 / `--only-l7`=40 / `--only-l6 --only-l7`=60 を確認。
追加テスト `tests/test_ledgers.py`（台帳選択マトリクス）・`tests/test_certify_merge.py`
（`merge_results` の後勝ち・モデル名連結・runs混在）で検証。

---

# 🆕 L7 grandmaster tier (t061–t100) — 任意オプション `--with-l7`

L6 architect でも上位帯(27B dense)がほぼ踏破し（最上位2モデル差=実質1問、生きた弁別
タスクは t059/t047/t046/t043 の4問程度）、再び天井効果が発生。**天井評価用の40問
(L7 grandmaster)** を追加しました。**既定の挙動は不変**（従来どおり40問、`--with-l6`
で60問）で、`--with-l7` を付けたときだけ +40 されます。

| 追加 | 内容 |
|---|---|
| 🏔️ L7 grandmaster (t061–t100, 40問) | 5軸×8問: 数値安定性(t061-068) / 状態一貫性(t069-076) / 複数結合バグ(t077-084) / 深い並行性(t085-092) / 敵対的パース・セキュリティ(t093-100)。issueは症状のみ |
| 🔀 `--with-l7` / `--l7-ledger` | 別台帳 `tasks/tasks_l7.jsonl` を任意マージ（既定40 → 80、`--with-l6`併用で100）。既存台帳は不変 |
| 🕵️ 隠密性基準（新） | 全40問で buggy が `test_core`（回帰罠）を通過＝lintや正常系では見えないバグのみ |
| 🎓 certify L7 gate | `grandmaster→L7`、暫定 pass@1 ≥ 35% かつ combined ≥ 55（実モデル較正で確定） |

**検証**: L7 selfcheck 40/40（gold緑/buggy赤/隠密性✓/ruff0）、軸Cは部分修正の不合格性、
軸Dは gold 10回連続緑・buggy 10/10失敗の決定性を確認。`validate --with-l7`
gold 40/40・broken 40/40、`list-tasks` 40（既定）/ 80（`--with-l7`）/ 100（`--with-l6 --with-l7`）。
t098 のみ `perf_timeout: 30`（ReDoS性能検証）。

---

# 🆕 `--concurrency`（試行の並列実行）— 総時間短縮オプション

`--runs N` の各試行を同時実行する `--concurrency K`（既定1=直列）を追加。
llama.cpp を `--parallel K -cb` で起動した場合に有効。`run.concurrency` でも既定値を設定可。

| 追加 | 内容 |
|---|---|
| 🔀 `--concurrency K` / `run.concurrency` | 試行(runs)を `ThreadPoolExecutor` で並列化（`min(K, runs)`）。MockClient は直列フォールバック |

**トレードオフ**: 総終了時間↓（実測 約2.2倍速）／1ストリーム tok/s↓（264→110）。
正答率・品質は不変。速度計測は `--concurrency 1` 推奨。

---

# 🆕 L6 architect tier (t041–t060) — 任意オプション `--with-l6`

frontier(L5)でも上位帯(27B〜35B級)が再び天井効果を起こすため、**さらに難しい
20問 (L6 architect)** を追加しました。**既定の挙動は不変**（従来どおり40問）で、
`--with-l6` を付けたときだけ +20 されます。

| 追加 | 内容 |
|---|---|
| 🏛️ L6 architect (t041–t060, 20問) | 複数ファイル8 / 非機能(perf)6 / 曖昧仕様4 / 罠・敵対2。issueは症状のみ |
| 🔀 `--with-l6` / `--l6-ledger` | 別台帳 `tasks/tasks_l6.jsonl` を任意マージ（既定40 → 60）。`tasks.jsonl` は不変 |
| 🧩 複数台帳ローダ | `load_tasks(..., ledgers=[...])`（id先勝ち）・`BenchmarkRunner(ledgers=...)` |
| 🎓 certify L6 gate | `architect→L6`、暫定 pass@1 ≥ 55% かつ combined ≥ 60（実モデル較正で確定） |

**検証**: L6 selfcheck 20/20（gold緑/buggy赤/ruff0/CC A–B）、`validate --with-l6`
gold 20/20・broken 20/20、`list-tasks` 40（既定）/ 60（`--with-l6`）。

---

# 難問tier (L4/L5) + 使えるライン認証 (certify)

上位ローカルコーダーが既存20問(easy/medium/hard)で頭打ちになり差がつかない
**天井効果**を解消するため、難問tierを追加し、「ここまでクリアできれば使える」を
tier合格制で判定する仕組みを導入しました。

| 追加 | 内容 |
|---|---|
| 🧩 L4 expert (t021–t032, 12問) | 仕様の細部・アルゴリズム正確性を問う難問 |
| 🧩 L5 frontier (t033–t040, 8問) | 複数ファイル・回帰罠・性能制約。4問は2つの結合バグ入り |
| 📝 症状ベースの issue | 新tierは修正手順を書かず**原因診断**を要求 (天井効果の主因対策) |
| 🎓 `llmbench certify` | 難易度→tier(L1-L5)、**L4独立合格=使えるライン**を判定 |
| ⏱️ per-task `perf_timeout` | 性能制約タスク向けにタスク別タイムアウトを採用 |

**検証**: selfcheck 新20問 20/20、`llmbench validate` 40/40 (gold全緑/broken全失敗)、
`llmbench list-tasks` total 40 (easy5/medium5/hard10/expert12/frontier8)。

> 較正メモ: 3モデル(7b/14b/30b)×5の実測で死蔵タスク・難易度逆転・issueの過剰ヒントを
> 検出し、issue症状化・frontier 2バグ化・certify非累積化に反映済み。tier閾値
> (`DEFAULT_GATES`) は暫定で、難化後の再実行で確定予定。

---

# 🆕 llmbench 機能追加（「実際どれくらい使えるか」を測る）

「ベンチのスコアは出るが、実際どれくらい使えるか分かりづらい」を解消するため、
**参照モデル比較 / pass@k信頼性 / usabilityティア / 難タスク** の4機能を追加し、
さらに **モデル運用の簡素化（model:auto・Ollama動的）** と **レポート表示の改善** を加えました。

> 本ファイルは新機能の要約・使い方・検証結果です。
> 詳しい運用は `MANUAL.md`（既存）、利用手順は `USAGE.md` を参照。

---

## なぜこの4つか

ベンチ結果が「使えるか」に直結しなかった理由は2つ。**基準（アンカー）がない**ことと、
**タスクが天井に張り付いて差が出ない**こと。さらに「使える＝最高スコア」ではなく
**使える＝成功率 × 信頼性 × 速度**です。これを測れるようにしました。

| 機能 | 解決する問題 |
|---|---|
| ① 参照モデル比較 (`compare`) | 94.3点が高いか低いか分からない → 強/弱モデルと並べて位置づけ |
| ② pass@k 信頼性 (`--runs`) | 1回成功＝使えるではない → N回試して成功率・pass@kを計測 |
| ③ usabilityティア | 数値が行動に落ちない → 自律/補助/不可に翻訳 |
| ④ 難タスク t016–t020 | 全問100%で差が出ない → 失敗が出る実務的タスクで天井を作る |

---

## ① 参照モデル比較 `compare`

複数の `results.json` を横断比較するレポートを生成します。APIキーは環境変数で渡せます
（`config.yaml` に `${OPENAI_API_KEY}` で参照する `ref-gpt` を追加済み）。

```bash
export OPENAI_API_KEY=sk-...
llmbench run --model local-openai --output results   # 自分のモデル
llmbench run --model ref-gpt      --output results   # 強い参照(API)
llmbench compare results/*_results.json --output results
```

出力（`comparison_<stamp>.md`）には、Combined降順のランキング（相対スコア＝最良比）、
usabilityティア比較、タスク別Combinedマトリクス（行内ベストを太字）が並びます。

## ② pass@k 信頼性 `--runs N`

各タスクをN回サンプリングし、成功率・pass@1・pass@k（Chen et al. 2021 の不偏推定量）を計測。
複数試行時は `combined = success_rate × (...)` となり、**信頼性がスコアに反映**されます。

```bash
llmbench run --model local-openai --runs 5            # 5回試行
llmbench run --model local-openai --runs 5 --sample-temp 0.8
```

- `runs=1`（既定）では従来と同じ挙動・数値（`combined` は `resolved×(...)` と一致）。
- 部分成功は `flaky 3/5 passed` と記録され、レポートに成功率・pass@k列が増えます。

## ③ usabilityティア

`success_rate` と `quality` から各タスクを **🟢自律 / 🟡補助 / 🔴不可** に分類し、
難易度×ティアのマトリクスと総合判定をレポートに出力します。しきい値は `config.yaml`:

```yaml
usability:
  autonomous: {min_success: 0.9, min_quality: 80}   # レビューほぼ不要
  assisted:   {min_success: 0.6, min_quality: 0}    # レビュー前提なら可
  # 上記未満は unusable
```

`results.json` の `summary.usability` と各タスクの `usability_tier` にも入ります。

## ④ 難タスク t016–t020（全hard）

意図的に失敗が出る、実務的な難しさのタスクを5つ追加（天井を作るため）。

| ID | テーマ | 難しさの種類 |
|---|---|---|
| t016 | 気温集計 (convert.py + report.py) | **複数ファイル**両方の修正が必要 |
| t017 | slugify | **曖昧仕様**（エッジケースを推測） |
| t018 | プラグインregistry | **既存の抽象（デコレータ）の理解** |
| t019 | トライ木 search/starts_with | **状態バグ**（語末フラグ欠落） |
| t020 | 式評価器 | **優先順位・括弧のリファクタ** |

---

## ⑤ モデル運用の簡素化（config編集レス）

ggufやモデルを差し替えるたびに `config.yaml` を書き換える手間をなくしました。

- **`model: auto`** — 起動時に `/v1/models` からサーバのロード中モデルを自動採用。
  レポート/結果ファイルも**その実モデル名でラベル**（`.gguf` は除去）。
- **Ollama動的選択** — config未定義でも `--model <インストール済み名>` を直接指定可
  （`/api/tags` から自動解決）。`llmbench models` で config + Ollama稼働モデルを一覧。
- **`--label <名前>`** — ラベルを明示固定したいとき。
- **APIキーの環境変数展開** — `api_key: "${OPENAI_API_KEY}"` で直書き回避。

## ⑥ レポートの信頼性表示を改善（誤読の解消）

- **pass@1（成功率）を主指標化** — `pass@5` は k=runs で退化（1回でも通れば1.0）し
  誤解を生むため撤去。「平均成功率(pass@1)」と「≥1成功できたタスク」を分離表示。
- **総合判定を保守的に** — 最頻ティアでの楽観表示をやめ、難易度別の割合＋
  「🔴不可が1つでもあれば自律と言い切らない」推奨に変更。
- **品質内訳に注記** — 多試行時、内訳は代表1試行・Qualityは平均である旨を明示。

---

## 変更ファイル

追加: `llmbench/usability.py`, `llmbench/compare.py`, `tasks/t016_temps〜t020_calc/`
変更: `llmbench/{runner,report,scoring,cli}.py`, `llmbench/clients/{openai_compat,ollama}.py`, `config.yaml`

## 検証結果（すべてPASS）

- `llmbench validate` … **gold 20/20 resolved・broken 20/20 fail・PASS**（全20タスク）。
- 新タスクの妥当性 … buggy_codeは全タスクでテスト失敗、gold適用で全タスク合格を個別確認。
- pass@k単体 … 後方互換（`combined(True,88.6)=94.3`）、不偏推定量の値、flaky/不可分類を確認。
- マルチラン実行 … 成功率・pass@k・usabilityの集計とレポート/JSON出力を確認。
- compare … ランキング・相対スコア・マトリクス・APIキー環境変数展開を確認。
- モデル解決 … `model:auto` のサーバ検出・ラベル整形・Ollama動的解決・未起動時の親切エラーを確認。
- ruff（E,F,W,B,SIM,C4,S）… 追加・変更ファイルは指摘ゼロ。`compileall` OK。

## 後方互換・移行メモ

- `runs=1` では既存フィールドの値は不変。`results.json` には追加フィールド
  （`runs` `success_rate` `pass_at_1` `pass_at_k` `attempts` `usability_tier`、
  `summary.usability` `solved_any_rate` ほか）が**増えます**。
- `report.md` のタスク別結果に **「判定（ティア）」列**が常時追加され、複数試行時はさらに
  **「信頼性」列**が増えます。Markdown表を機械パースしている場合は列数の変化に注意。
- サマリの `pass@k` 行は撤去し、`成功率(pass@1)` と `≥1成功` に変更（⑥）。
