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
- ⚖️ **複合スコア** — 動かないコードは0点。動くコードを品質で差別化
- 🔌 **接続2系統** — OpenAI互換API (llama.cpp / LM Studio / vLLM) と Ollama 両対応。configのbase_url切替だけでモデル比較
- 🇯🇵 **日英issue同梱** — `--lang ja` で「language tax」(日本語指示による性能低下)を計測可能
- ⚡ **速度計測** — タスク別レイテンシ / tok/s をレポートに自動記録
- 📦 **同梱タスク15個** — easy / medium / hard 各5。外部依存なし(stdlib-only)で即実行
- 🛡️ **安全設計** — テストはLLMに非公開、patch書込先は既知ファイルに限定、元タスクは不変

## 🚀 クイックスタート

```bash
git clone https://github.com/zephel01/swe-bench.git
cd swe-bench
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 1️⃣ 自己検証 (LLM不要 — モックでパイプライン全体を確認)
llmbench validate

# 2️⃣ config.yaml の base_url / model を自分の環境に編集

# 3️⃣ 実行
llmbench run --model local-ollama
llmbench run --model local-openai --tasks t001,t011 --lang ja
```

結果は `results/` に JSON + Markdown レポートで保存されます。

<details>
<summary>📄 レポート出力例</summary>

```markdown
# llmbench レポート: local-ollama

- Resolved率: 73.3%
- 品質平均 (resolvedのみ): 84.2/100
- Combined平均: 67.5/100

| Task | 難易度 | Resolved | Quality | Combined | 生成時間(s) | tok/s |
|---|---|---|---|---|---|---|
| t001 | easy   | O | 95 | 98 | 4.2  | 62.1 |
| t011 | hard   | X | 0  | 0  | 18.9 | 58.3 |
```

</details>

## 📊 スコアリング

```
combined = resolved × (0.5 + 0.5 × quality / 100) × 100
```

| resolved | quality | combined | 意味 |
|---|---|---|---|
| ❌ | — | **0** | 動かないコードは品質に関わらず0点 |
| ✅ | 0 | **50** | 動くが品質最低 |
| ✅ | 100 | **100** | 動いて品質も完璧 |

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
    model: "qwen2.5-coder-32b-instruct"
  local-ollama:
    type: ollama
    base_url: "http://localhost:11434"
    model: "qwen2.5-coder:32b"

run:
  issue_lang: en           # ja に切替で language tax 検証
  test_timeout: 120

quality:
  llm_review:
    enabled: false         # レビュー用モデル稼働時に true
    reviewer_model: local-openai
```

## 📁 プロジェクト構成

```
swe-bench/
├── llmbench/
│   ├── clients/        # 🔌 LLM接続 (openai_compat / ollama / mock)
│   ├── patch.py        # 📝 LLM出力パース (FILE:マーカー + コードブロック)
│   ├── sandbox.py      # 📦 一時コピー + pytest隔離実行
│   ├── functional.py   # ✅ resolved判定
│   ├── quality/        # 🧹 ruff / complexity / llm_review / sonar
│   ├── scoring.py      # ⚖️ 複合スコア
│   ├── runner.py       # 🎛️ オーケストレータ
│   └── report.py       # 📊 Markdownレポート
├── tasks/              # 🧩 同梱タスク15個 (easy/medium/hard × 5)
└── config.yaml
```

> [!NOTE]
> patch形式は「ファイル全体置換」(`--- FILE: path ---` + コードブロック) を採用。
> ローカルLLMはunified diffの行番号精度が低いため、この方式の方がパース成功率が高い。

## 🧩 タスクの追加

> 📋 同梱15タスクの詳細仕様 (調査対象・採点基準) は **[TASKS.md](TASKS.md)** を参照。

```
tasks/tXXX_name/
├── issue.md        # 英語バグレポート
├── issue_ja.md     # 日本語バグレポート
├── buggy_code/     # バグ入りソース (LLMに渡される)
├── gold/           # 正解ファイル (変更が必要なファイルのみ)
└── tests/          # 隠しテスト (LLMには渡されない)
```

1. 上記レイアウトでディレクトリを作成
2. `tasks/tasks.jsonl` に1行追加:
   ```json
   {"task_id": "t016", "dir": "t016_name", "difficulty": "medium", "title": "..."}
   ```
3. 検証: `llmbench validate --tasks t016` (gold がpass / broken がfail すればOK)

## 🗺️ ロードマップ

- [x] 機能 + 品質の複合評価パイプライン
- [x] OpenAI互換 / Ollama 両対応
- [x] 日英issueによる language tax 計測
- [ ] 🐳 Docker隔離実行
- [ ] 📥 SWE-bench Lite 公式タスクの取込
- [ ] 🔄 GitHub repoからのタスク自動抽出
- [ ] 📈 nvidia-smiによるVRAM自動計測
- [ ] 🆚 複数モデル一括比較レポート

## 🤝 Contributing

タスク追加・品質レイヤー追加のPR歓迎です。`llmbench validate` がPASSすることを確認の上、Conventional Commits形式 (`feat:` / `fix:`) でお願いします。

## 📜 License

[MIT](LICENSE)
