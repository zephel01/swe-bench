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
| `--ctx-size` や量子化の選び方を決めたい | [GGUF_PROBE.md](GGUF_PROBE.md) |
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
detection（脆弱性検出）/ constraint（指示追従）/ judge（創作）/ qa（医療QA）。

### 🔍 [GGUF_PROBE.md](GGUF_PROBE.md) — gguf_probe の使い方

GGUF を読むだけで `--ctx-size` の上限・KV キャッシュの VRAM・
`--spec-type draft-mtp` の可否が決まります。**GPU を回す前**に読むもの。

### 📝 [CHANGES.md](CHANGES.md) — 変更履歴

追加機能の要約と変更履歴。

---

## ここに無いもの

- **`_OUTPUTS/`** — 検証メモ・記事の下書き・設計書の置き場。`.gitignore` 対象の
  ローカル作業フォルダで、追跡されません
- **`llmbench --help` / `llmbench <cmd> --help`** — オプションの正確な一覧は
  ドキュメントより実物が確実です
