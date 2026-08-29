# 📚 llmbench ドキュメント索引

まず読むのは [../README.md](../README.md)（概要・特徴・スコア定義）です。
そこから先、**やりたいことごと**にここから辿ってください。

---

## 目的別

| やりたいこと | 読むもの |
|---|---|
| インストールして1本走らせたい | [USAGE.md](USAGE.md) 1〜5章 |
| レポートや `results.json` の読み方を知りたい | [USAGE.md](USAGE.md) 9〜13章 |
| モデルを横断比較したい | [USAGE.md](USAGE.md) 8章 / `compare` |
| 「使えるライン」を判定したい | [USAGE.md](USAGE.md) 8.5章 / `certify` |
| 出力ファイルの**仕様**を知りたい（他システム連携） | [MANUAL.md](MANUAL.md) 2章 |
| 内部実装を追いたい・保守したい | [MANUAL.md](MANUAL.md) 3章 |
| CI に組み込みたい | [MANUAL.md](MANUAL.md) 5章 |
| タスクを追加・修正したい | [TASKS.md](TASKS.md) |
| コーディング以外の採点軸を足したい | [DESIGN_DOMAINS.md](DESIGN_DOMAINS.md) |
| 日本のネットミーム知識・拒否率を測りたい | [../README.md](../README.md#-日本ネットミーム-ベンチ-culture) / [TASKS.md](TASKS.md) |
| 過剰拒否 (over-refusal) を測りたい | [../README.md](../README.md#-過剰拒否-ベンチ-uncensored) / [DESIGN_UNCENSORED.md](DESIGN_UNCENSORED.md) / [TASKS.md](TASKS.md) |
| `--ctx-size` や量子化の選び方を決めたい | [GGUF_PROBE.md](GGUF_PROBE.md) |
| GPU を回す前に「この量子化は載るか」を知りたい | [GGUF_PROBE.md](GGUF_PROBE.md)「実用的な使い方」 |
| 量子化を切り替えて総当たりで測りたい | [SWEEP.md](SWEEP.md) |
| モデル追加からレポートまでを一気通貫で回したい | [AUTOMATION.md](AUTOMATION.md) |
| 長いランを無人で流し、途中で止まっても再開したい | [AUTOMATION.md](AUTOMATION.md) 4章 |
| 比較条件が揃っているかを確認したい | [AUTOMATION.md](AUTOMATION.md) 5章 |
| いつ何が変わったか調べたい | [CHANGES.md](CHANGES.md) |

---

## ファイル別

### 📘 [USAGE.md](USAGE.md) — 利用ガイド

インストールからモデル比較、**生成物 (artifacts) を使った結果の読み解き方**まで。
日常的に開くのはこれです。

### 🛠️ [MANUAL.md](MANUAL.md) — 運用マニュアル

`results.json` / `report.md` / `artifacts/` の**出力仕様**、内部実装、
ディスク・保持・git の運用注意、CI連携、プログラムからの結果アクセス。
「llmbench の出力を他のものに食わせる」ときに読みます。

### 🧩 [TASKS.md](TASKS.md) — タスク台帳

全タスクの一覧と設計意図。難易度帯（L1 easy 〜 L7 grandmaster）ごとの狙い、
grader 別のディレクトリ構成と gold スキーマ。**タスクを足すとき**はここ。

### 📐 [DESIGN_DOMAINS.md](DESIGN_DOMAINS.md) — マルチドメイン拡張 仕様書

コーディング以外を測る **pluggable grader** の設計。
detection（脆弱性検出）/ constraint（指示追従）/ judge（創作）/ qa（医療QA）、
および既存graderを流用する culture（日本ネットミーム知識＋拒否検出）と
uncensored（過剰拒否検査。詳細は [DESIGN_UNCENSORED.md](DESIGN_UNCENSORED.md)）。

### 🔓 [DESIGN_UNCENSORED.md](DESIGN_UNCENSORED.md) — 過剰拒否ドメイン 仕様書

無害で正解が確定する問いに、拒否を誘発しやすい語を添えて出す over-refusal 検査。
jailbreak ベンチではない。現行タスクは 12 問＝12 誘発タイプ。一覧は [TASKS.md](TASKS.md)。

### 🔍 [GGUF_PROBE.md](GGUF_PROBE.md) — `gguf_probe` と `gguf_plan` の使い方

GGUF を読むだけで `--ctx-size` の上限・KV キャッシュの VRAM・
`--spec-type draft-mtp` の可否が決まります。**GPU を回す前**に読むもの。

`gguf_probe.py` が読み、`gguf_plan.py` が VRAM 予算から
`llama-server` の起動コマンドと `config.yaml` を出します。
場面別の使い方（量子化を絞る／ctx を決める／ctx が足りないとき）も載せています。

### 🤖 [AUTOMATION.md](AUTOMATION.md) — 自動化ガイド

新しいモデル / 量子化が来てから比較レポートを出すまでの**順序と判断**。
gguf を調べる → 条件を実測で決める → `sweep.conf` に固定する → 無人で回す →
条件が揃っていたかを検証する → `compare` / `certify` でまとめる。
実運用で踏んだ詰まり方の早見表と、走らせる前のチェックリスト付き。
**モデルが増えるたびに開くもの**です。

### 🔁 [SWEEP.md](SWEEP.md) — 量子化スイープ (`tools/sweep.sh`)

`llama-server` の起動 → `llmbench run` → 停止 を量子化ごとに繰り返すバッチの使い方。
どのスイート (l6 / l7 / culture / unc) を何 runs で回すか、量子化ごとの起動引数の上書き、
resume と出力の見方。**同じモデルの量子化を横断で測るとき**はここ。

### 📝 [CHANGES.md](CHANGES.md) — 変更履歴

追加機能の要約と変更履歴。

---

## ここに無いもの

- **`_OUTPUTS/`** — 検証メモ・記事の下書き・設計書の置き場。`.gitignore` 対象の
  ローカル作業フォルダで、追跡されません
- **`llmbench --help` / `llmbench <cmd> --help`** — オプションの正確な一覧は
  ドキュメントより実物が確実です
