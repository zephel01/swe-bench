# 🆕 llmbench 機能追加（「実際どれくらい使えるか」を測る4機能）

「ベンチのスコアは出るが、実際どれくらい使えるか分かりづらい」を解消するため、
**参照モデル比較 / pass@k信頼性 / usabilityティア / 難タスク** の4つを追加しました。

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

## 変更ファイル

追加: `llmbench/usability.py`, `llmbench/compare.py`, `tasks/t016_temps〜t020_calc/`
変更: `llmbench/{runner,report,scoring,cli}.py`, `llmbench/clients/openai_compat.py`, `config.yaml`

## 検証結果（すべてPASS）

- `llmbench validate` … **gold 20/20 resolved・broken 20/20 fail・PASS**（全20タスク）。
- 新タスクの妥当性 … buggy_codeは全タスクでテスト失敗、gold適用で全タスク合格を個別確認。
- pass@k単体 … 後方互換（`combined(True,88.6)=94.3`）、不偏推定量の値、flaky/不可分類を確認。
- マルチラン実行 … 成功率・pass@k・usabilityの集計とレポート/JSON出力を確認。
- compare … ランキング・相対スコア・マトリクス・APIキー環境変数展開を確認。
- ruff（E,F,W,B,SIM,C4,S）… 追加・変更ファイルは指摘ゼロ。`compileall` OK。

## 後方互換・移行メモ

- `runs=1` では既存フィールドの値は不変。`results.json` には追加フィールド
  （`runs` `success_rate` `pass_at_1` `pass_at_k` `attempts` `usability_tier`、
  `summary.usability` ほか）が**増えます**。
- `report.md` のタスク別結果に **「判定（ティア）」列**が常時追加され、複数試行時はさらに
  **「信頼性」列**が増えます。Markdown表を機械パースしている場合は列数の変化に注意。

## 配置方法

`llm-bench-v2.tar.gz` を展開するか、`_OUTPUTS/llm-bench-v2/` の各ファイルをリポジトリへコピー。
本体への反映やPR化はご指示ください（feature ブランチ運用に従います）。
