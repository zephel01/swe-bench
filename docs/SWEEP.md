# 🔁 量子化スイープ (`tools/sweep.sh`)

手で `llama-server` を起動 → `llmbench run` → 落として次の gguf、を繰り返していた作業を
1コマンドにしたもの。**量子化 × スイート**の総当たりを順に流す。

```
for 量子化 in Q4_K_M Q6_K Q8_0:
    llama-server 起動 → /health が通るまで待つ → 実ロードモデルを記録
    for スイート in l6 l7 culture unc:
        llmbench run --model local-openai <台帳フラグ> --runs N --label <量子化>-<スイート>
    llama-server 停止 → VRAM 解放を待つ
サマリ表を出す
```

`llama-server` と gguf があるマシン（GPU機）で実行します。

```bash
chmod +x tools/sweep.sh
cp tools/sweep.conf.example sweep.conf   # パスを自分の環境に直す
tools/sweep.sh -c sweep.conf --list      # まず対象を確認
tools/sweep.sh -c sweep.conf --dry-run   # コマンドだけ見る
tools/sweep.sh -c sweep.conf             # 本番
```

`REPO_DIR` の既定は「スクリプトの1つ上のディレクトリ」なので、`tools/` に置いたままなら
clone 先を問わず書き換え不要です。`sweep.sh` 冒頭にも同じ設定が全部入っているので、
`sweep.conf` を使わず**スクリプトを直接書き換えても**動きます。
優先順位は **CLI > `sweep.conf` > 環境変数 > スクリプト冒頭の既定値**。

---

## 1. どのスイートをやるか

やらないスイートがある前提なので、指定方法を3つ用意しています。

| やり方 | 例 |
|---|---|
| スクリプト冒頭 / conf の ON/OFF | `RUN_L6=0` … l6 をやらない |
| 環境変数で一時的に | `RUN_CULTURE=0 RUNS_L7=5 tools/sweep.sh` |
| CLI で明示 | `tools/sweep.sh --suites l7,unc`（書いたものだけ実行）<br>`tools/sweep.sh --skip l6`（これだけ外す） |

スイートと展開されるコマンドの対応:

| スイート | 展開されるコマンド | 既定 runs |
|---|---|---|
| `l6` | `llmbench run --model local-openai --with-l6` | 5 |
| `l7` | `llmbench run --model local-openai --only-l7` | 3 |
| `culture` | `llmbench run --model local-openai --only-culture --lang ja` | 3 |
| `unc` | `llmbench run --model local-openai --only-unc` | 3 |

runs は `RUNS_L6` / `RUNS_L7` / `RUNS_CULTURE` / `RUNS_UNC` で個別に、`--runs N` で全部まとめて
変えられます。台帳フラグ自体を変えたいときは `ARGS_L7="--only-l7 --with-sec"` のように
`ARGS_*` を書き換えます。

スイートを増やすときは `RUN_<名前>` / `RUNS_<名前>` / `ARGS_<名前>` の3つを足して
`SUITE_ORDER` に名前を追加するだけです（例: `RUN_SEC=1 RUNS_SEC=3 ARGS_SEC="--only-sec"`）。

---

## 2. どの量子化をやるか

```bash
QUANTS="Q4_K_M Q6_K Q8_0"      # 明示リスト (カンマ区切りも可)
QUANTS=auto                    # MODEL_DIR の *.gguf を全部 (ファイル名順)
QUANT_EXCLUDE='UD-'            # auto のときの除外正規表現
tools/sweep.sh --quants Q4_K_M,Q6_K
```

gguf は `<MODEL_PREFIX>-<量子化>.gguf` として探します（例: `Qwen3.8-27B-Q6_K.gguf`）。
見つからないときは `*<量子化>*.gguf` で拾い、分割 gguf は `-00001-of-000NN` を渡します。
見つからなければその量子化は `no_model` として記録し、**次へ進みます**（全体は止まりません）。

---

## 3. llama-server の起動引数

共通テンプレ + 量子化ごとの上書き。上書きは共通引数の**後ろ**に付くので、同じ引数なら後勝ちです。

```bash
# 共通
NGL=99 FLASH_ATTN=on CTX=65536 PARALLEL=1 BATCH=2048 UBATCH=512
# 大きい量子化だけ ctx を落として KV を量子化する
OVERRIDE_Q6_K="--ctx-size 32768 -ctk q8_0 -ctv q8_0"
```

実際に発行されるコマンド:

```
llama-server -m <gguf> --host 127.0.0.1 --port 8085 \
  -ngl 99 --ctx-size 65536 --parallel 1 --batch-size 2048 --ubatch-size 512 -fa on \
  [-ctk/-ctv <KV_TYPE>] [--device …] [--tensor-split …] [SERVER_EXTRA_ARGS] [OVERRIDE_<量子化>]
```

変数名は `OVERRIDE_<量子化名>`。`.` と `-` は `_` に置換します
(`UD-Q4_K_XL` → `OVERRIDE_UD_Q4_K_XL`)。

VRAM 予算から `--ctx-size` と KV 量子化を決める手順は
[GGUF_PROBE.md](GGUF_PROBE.md) を参照してください（`gguf_plan.py` が出す起動コマンドの
値をそのまま `OVERRIDE_*` に写せます）。

`--parallel` を上げるときは `CONCURRENCY`（= `llmbench --concurrency`）も同じ値にすること。
サーバ側とベンチ側で並列数が食い違うと計測条件が揃いません（[USAGE.md](USAGE.md) 8.5章）。

---

## 4. ⚠️ seed の扱い

`config.yaml` の `local-openai` には `seed: 42` が入っています。config 自身のコメントにある通り、
**`runs > 1` で seed を固定すると全試行が同一条件になり pass@k の前提が崩れます**。
スイープの既定スイートは全部 `runs 3〜5` なので、次のように扱います。

- `STRIP_SEED_FOR_MULTIRUN=1`（既定）… `runs>1` のスイートだけ、`local-openai` ブロックの
  `seed:` 行をコメントアウトした一時 config（`_OUTPUTS/sweep/config_noseed.yaml`）を
  `--config` に渡す。**元の `config.yaml` は読むだけで書き換えません。**
- `runs=1` のスイートには元の `config.yaml` をそのまま使う。
- `STRIP_SEED_FOR_MULTIRUN=0` にすれば何もしない。

一時 config は `models:` の該当ブロックだけを見るので、`local-openai-lowtemp` や `run:` の
seed には触りません。

---

## 5. 出力

| もの | 場所 |
|---|---|
| ベンチ結果 | `results/<日時>_<量子化>-<スイート>_results.json` / `_report.md`（`--label` で命名） |
| サーバ/ベンチのログ | `_OUTPUTS/sweep/logs/<実行ID>/<量子化>_{server,l7,unc,…}.log` |
| 実ロード確認 | `_OUTPUTS/sweep/logs/<実行ID>/<量子化>_props.json` / `_models.json` |
| 条件の一覧 | `_OUTPUTS/sweep/manifest_<実行ID>.tsv`（量子化 / サーバが返したモデルID / n_ctx） |
| サマリ | `_OUTPUTS/sweep/summary_<実行ID>.tsv` + 標準出力の表 |
| 進捗（resume用） | `_OUTPUTS/sweep/sweep_state.tsv` |

`manifest_*.tsv` は「その量子化で本当に何がロードされ、n_ctx はいくつだったか」を
サーバの `/props` `/v1/models` から取って残したものです。量子化間の比較は**推論条件が
揃っているときだけ**成立する（[USAGE.md](USAGE.md) 13章）ので、比較レポートを書く前に
ここを確認してください。

最後にスイートごとの横断比較コマンド（`llmbench compare …`）を出力するので、そのまま貼れば
量子化間の比較レポートが作れます。

---

## 6. 途中で落ちたとき

- 既定は **`--resume`**。`sweep_state.tsv` に `ok` で残っている（量子化, スイート）は飛ばします。
  その量子化が全部済んでいればサーバも起動しません。
- 全部やり直すときは `--no-resume`、または `sweep_state.tsv` を消します。
- 1スイートが失敗しても既定では次に進みます（`KEEP_GOING=1`）。そこで止めたいなら `--stop-on-error`。
- Ctrl-C / kill されても trap で `llama-server` を必ず停止します（VRAM が掴まれたままになりません）。
- 終了コードは、失敗が1つでもあれば 1、全部成功なら 0。

---

## 7. オプション一覧

```
-c, --conf FILE      追加設定ファイル
    --quants LIST    対象量子化 (カンマ/スペース区切り、"auto" 可)
    --suites LIST    実行スイート (例: l7,unc)。指定外は実行しない
    --skip LIST      指定スイートだけ外す
    --runs N         全スイートの --runs を N に上書き
    --ctx N          --ctx-size
    --port N         llama-server のポート
    --model-dir DIR  gguf の置き場
    --results DIR    llmbench --output の出力先
    --timeout SEC    1スイートの上限秒 (0=無制限)
    --skip-preflight llmbench の preflight を省略
    --no-resume      完了済みでも再実行
    --force-port     ポートを掴んでいる既存プロセスを落としてから起動
    --stop-on-error  失敗したら打ち切る
-n, --dry-run        実行せずコマンドを表示
-l, --list           実行対象を表示して終了
-h, --help           ヘルプ
```

---

## 8. 前提

- bash 4以上、`curl`、`python3`（`/props` の読み取りのみ）。`flock` があれば二重起動を防ぎます。
- `llama-server` の `/health` `/props` `/v1/models` が有効であること。
- `config.yaml` の `local-openai` は `model: "auto"` のままでよい
  （サーバの `/v1/models` からロード中モデルを自動採用するので、gguf を差し替えても
  config 編集は不要 — [USAGE.md](USAGE.md) 3章）。
- `http_proxy` が設定された環境でも localhost がプロキシに吸われないよう、
  スクリプト内の `curl` は必ず `--noproxy '*'` を付けています。

---

## 9. 検証状況

スタブ環境（`/health` が 503→200 に変わる偽 `llama-server` と、サーバ到達を確認して
`results.json` を吐く偽 `llmbench`）で、対象解決・通し実行・gguf 不在・サーバ起動失敗・
スイート異常終了・実行中の SIGINT・resume・conf 上書き・seed 無効化の切り替わりを確認済み
（2026-08-29 / 15ケース）。

**実 `llama-server` と実 gguf を使った通し実行は未検証**です。初回は
`--list` → `--dry-run` → 量子化1つ + スイート1つ、の順で試してください。
