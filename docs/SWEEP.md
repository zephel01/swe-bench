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
cp tools/sweep.conf.example tools/sweep.conf   # 自分の環境のパスを書く
tools/sweep.sh --list                          # まず対象を確認
tools/sweep.sh --dry-run                       # コマンドだけ見る
tools/sweep.sh                                 # 本番
```

`tools/sweep.conf` は `-c` を付けなくても自動で読まれます（`.gitignore` 済みなので、
個人の絶対パスを書いて構いません）。`-c` 省略時の探索順は次のとおり。

| 順 | 探す場所 |
|---|---|
| 1 | 環境変数 `SWEEP_CONF` |
| 2 | `tools/sweep.conf`（= スクリプトと同じディレクトリ） |
| 3 | `<リポジトリ>/sweep.conf` |

`-c FILE` で明示すればそれが最優先、`--no-conf` を付ければ何も読まずスクリプトの
既定値だけで走ります。どの設定を読んだかは `--list` と実行開始時のログに出ます。

`REPO_DIR` の既定は「スクリプトの1つ上のディレクトリ」なので、`tools/` に置いたままなら
clone 先を問わず書き換え不要です。`LLMBENCH` / `CONFIG` / `TASKS_DIR` / `OUT_ROOT` /
`RESULTS_DIR` は conf を読んだ後に `REPO_DIR` から導出されるので、conf で `REPO_DIR` だけ
書き換えれば残りも追随します（個別に別の場所を指したいときだけ、その変数を書く）。

`sweep.sh` 冒頭にも同じ設定が全部入っているので、conf を使わず**スクリプトを直接
書き換えても**動きます。優先順位は **CLI > conf > 環境変数 > スクリプト冒頭の既定値**。

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

### デバイス指定と VRAM

`DEVICE` は空なら llama.cpp が見えている全デバイスを使います。搭載構成に応じて指定します
（デバイス名は `llama-server --list-devices` で確認）。

| 構成 | 設定 |
|---|---|
| 1枚だけ使う | `DEVICE=CUDA0` |
| 2枚に分割する | `DEVICE=CUDA0,CUDA1` + `TENSOR_SPLIT=0.5,0.5` |
| 重い量子化だけ2枚 | `OVERRIDE_Q8_0="--device CUDA0,CUDA1 --tensor-split 0.5,0.5"` |
| ROCm / Vulkan | `DEVICE=ROCm0` / `DEVICE=Vulkan0` |

> ⚠️ **`-ngl 99` を付けていても、モデル + KV が VRAM に収まらなければ llama.cpp は
> 一部の層を CPU に置きます。** 生成は数十倍遅くなりますが、ログには何も出ません。

ただし **KV の大きさはモデルの構造で桁が変わるので、層数から推測してはいけません**。
`Qwen3.8-27B` は 65層のうち 17層だけがフル Attention（残り 48層は線形注意）で、
KV は **68 KB/token** しかありません。`--ctx-size 65536` でも 4.25 GiB です。

```bash
python gguf_probe.py <gguf>   # 「KVキャッシュ: 17/65 層が保持 = 68 KB/token」
```

RTX 5090 32GB / `Qwen3.8-27B-Uncensored` / ctx 65536 / KV f16 / MTP ありの実測:

| 量子化 | VRAM 使用 | 余裕（32,607 MiB 中） |
|---|---|---|
| Q4_K_M | 21,210 MiB | 11.4 GB |
| Q6_K | 26,258 MiB | 6.3 GB |

llama.cpp は KV を起動時に全確保するので、この値は **ctx を使い切った状態の値**です
（長いタスクでも増えません）。この構成では ctx を削る必要も KV を量子化する必要も
ありませんでした。

サーバ起動後、`sweep.sh` は `nvidia-smi` で **全 GPU の VRAM 使用量を合計してログと
manifest に記録**し、モデルファイルサイズの半分に満たなければ警告します。この警告が
出たら、そのランは CPU にこぼれていると考えて条件を見直してください。

VRAM 予算から `--ctx-size` と KV 量子化を決める正確な手順は
[GGUF_PROBE.md](GGUF_PROBE.md) にあります（`gguf_plan.py` が出す起動コマンドの
値をそのまま `OVERRIDE_*` に写せます）。

```bash
python gguf_probe.py --json --out gguf.json /llm/models/Qwen3.8-27B-GGUF/*.gguf
python gguf_plan.py gguf.json --vram 31 --pick Q4_K_M
```

### MTP（投機デコード）— 効くなら必ず付ける

`gguf_probe` が `MTP/nextn テンソル: N 本` と出せば、`N > 0` で
`--spec-type draft-mtp` が使えます。**検証付きなので出力は変わらず、速度だけ上がります。**

```sh
SERVER_EXTRA_ARGS="--spec-type draft-mtp"
```

RTX 5090 / `Qwen3.8-27B-Uncensored-Q4_K_M` / ctx 65536 / KV f16 での実測:

| 条件 | tok/s | VRAM |
|---|---|---|
| ctx 32768 / KV q8_0 | 73.7 | 17,164 MiB |
| ctx 65536 / KV f16 | 74.6 | 20,118 MiB |
| **+ `--spec-type draft-mtp`** | **136.3** | 21,210 MiB |

KV を q8_0 にしても速度はほぼ変わらず（-1%）、MTP は **1.84倍**でした。付け忘れると
スイープ全体の所要時間がそのまま倍になります。量子化ごとに MTP の有無が違うと比較条件が
崩れるので、**全量子化で `gguf_probe` を通してから**有効にしてください。

`--parallel` を上げるときは `CONCURRENCY`（= `llmbench --concurrency`）も同じ値にすること。
サーバ側とベンチ側で並列数が食い違うと計測条件が揃いません（[USAGE.md](USAGE.md) 8.5章）。

---

## 4. ⚠️ config の書き換え（seed / max_tokens）

`sweep.sh` は元の `config.yaml` を**読むだけ**で、必要な調整は
`_OUTPUTS/sweep/config_<量子化>[_noseed].yaml` という一時 config に対して行い、
それを `llmbench --config` に渡します。どの調整をしたかは実行ログに出ます。

```
config: config_Q4_K_M_noseed.yaml  [seed 無効化 / max_tokens 49152 → 24576 (ctx 32768)]
```

### max_tokens を実効 ctx に合わせる

`max_tokens >= n_ctx` だと実効上限が `n_ctx − プロンプト長` になり `max_tokens` が
効かないため、**preflight が FAIL になって実行できません**。`--ctx-size` を下げたときに
必ず踏みます（例: `config.yaml` の `max_tokens: 49152` のまま `CTX=32768` にすると FAIL）。

`ADJUST_MAX_TOKENS=1`（既定）なら、量子化ごとの**実効 ctx**（`CTX` を
`SERVER_EXTRA_ARGS` / `OVERRIDE_*` の `--ctx-size` が後勝ちで上書きした値）から
`min(ctx の 3/4, MAX_TOKENS_CAP)` を計算し、config の値より小さいときだけ引き下げます。
`gguf_plan.py` と同じ規則です。

| 設定 | 意味 |
|---|---|
| `ADJUST_MAX_TOKENS=0` | 何もしない（config の値をそのまま使う） |
| `MAX_TOKENS=8192` | 自動計算せずこの値にする |
| `MAX_TOKENS_CAP=49152` | 自動計算の上限（既定） |

**ctx を上げても max_tokens は勝手に増やしません**（下げる方向のみ）。量子化ごとに
ctx を変えると max_tokens も変わるので、比較条件が揃わなくなる点に注意してください。

---

## 5. ⚠️ seed の扱い

`config.yaml` の `local-openai` には `seed: 42` が入っています。config 自身のコメントにある通り、
**`runs > 1` で seed を固定すると全試行が同一条件になり pass@k の前提が崩れます**。
スイープの既定スイートは全部 `runs 3〜5` なので、次のように扱います。

- `STRIP_SEED_FOR_MULTIRUN=1`（既定）… `runs>1` のスイートだけ、`local-openai` ブロックの
  `seed:` 行をコメントアウトした一時 config（`_OUTPUTS/sweep/config_<量子化>_noseed.yaml`）を
  `--config` に渡す。**元の `config.yaml` は読むだけで書き換えません。**
- `runs=1` のスイートには元の `config.yaml` をそのまま使う。
- `STRIP_SEED_FOR_MULTIRUN=0` にすれば何もしない。

一時 config は `models:` の該当ブロックだけを見るので、`local-openai-lowtemp` や `run:` の
seed には触りません。

---

## 6. 出力

| もの | 場所 |
|---|---|
| ベンチ結果 | `results/<日時>_<量子化>-<スイート>_results.json` / `_report.md`（`--label` で命名） |
| サーバ/ベンチのログ | `_OUTPUTS/sweep/logs/<実行ID>/<量子化>_{server,l7,unc,…}.log` |
| 実ロード確認 | `_OUTPUTS/sweep/logs/<実行ID>/<量子化>_props.json` / `_models.json` |
| 条件の一覧 | `_OUTPUTS/sweep/manifest_<実行ID>.tsv`（量子化 / モデルID / n_ctx / VRAM 使用・総量 MiB） |
| サマリ | `_OUTPUTS/sweep/summary_<実行ID>.tsv` + 標準出力の表 |
| 進捗（resume用） | `_OUTPUTS/sweep/sweep_state.tsv` |

`manifest_*.tsv` は「その量子化で本当に何がロードされ、n_ctx はいくつだったか」を
サーバの `/props` `/v1/models` から取って残したものです。量子化間の比較は**推論条件が
揃っているときだけ**成立する（[USAGE.md](USAGE.md) 13章）ので、比較レポートを書く前に
ここを確認してください。

最後にスイートごとの横断比較コマンド（`llmbench compare …`）を出力するので、そのまま貼れば
量子化間の比較レポートが作れます。

---

## 7. 画面が止まって見えるとき

`preflight` の判定が出たあと、しばらく何も表示されないことがあります。多くの場合は
**止まっていません**。thinking モデルは1タスクに数分〜十数分かけるので、その間は出力が
ありません（`preflight` は stderr、ベンチの進捗は stdout に出ます）。

生きているかは、ベンチではなく**サーバ側**を見るのが確実です。

```bash
nvidia-smi                       # 使用率が上がっていれば生成中
tail -f _OUTPUTS/sweep/logs/<実行ID>/<量子化>_server.log
curl -s localhost:8085/health    # {"status":"ok"} が返る
```

**本当に遅い**場合は、まず VRAM を疑ってください。`sweep.sh` が起動直後に出す
`VRAM 合計: ... MiB` がモデルサイズを大きく下回っていれば、CPU にこぼれています
（前章「デバイス指定と VRAM」）。`nvidia-smi` の GPU 使用率が低いのに CPU が
張り付いているときも同じ症状です。

`preflight` の **WARN は続行します**（止まるのは FAIL のときだけ）。`seed` 未指定の
WARN は、`runs>1` のために意図的に seed を外しているぶんなので想定どおりです。

> 補足: 進捗は `tee` を通すと Python がブロックバッファリングに切り替わって
> 数KB 貯まるまで表示されません。`sweep.sh` は `PYTHONUNBUFFERED=1` を付けて
> 行ごとに流すようにしてあります。

---

## 8. 途中で落ちたとき

- 既定は **`--resume`**。`sweep_state.tsv` に `ok` で残っている（量子化, スイート）は飛ばします。
  その量子化が全部済んでいればサーバも起動しません。
- 全部やり直すときは `--no-resume`、または `sweep_state.tsv` を消します。
- 1スイートが失敗しても既定では次に進みます（`KEEP_GOING=1`）。そこで止めたいなら `--stop-on-error`。
- Ctrl-C / kill されても trap で `llama-server` を必ず停止します（VRAM が掴まれたままになりません）。
- 終了コードは、失敗が1つでもあれば 1、全部成功なら 0。

---

## 9. オプション一覧

```
-c, --conf FILE      設定ファイルを明示指定 (省略時は tools/sweep.conf を自動で読む)
    --no-conf        設定ファイルを読まない (スクリプト既定値だけで走る)
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

## 10. 前提

- bash 4以上、`curl`、`python3`（`/props` の読み取りのみ）。`flock` があれば二重起動を防ぎます。
- `llama-server` の `/health` `/props` `/v1/models` が有効であること。
- `config.yaml` の `local-openai` は `model: "auto"` のままでよい
  （サーバの `/v1/models` からロード中モデルを自動採用するので、gguf を差し替えても
  config 編集は不要 — [USAGE.md](USAGE.md) 3章）。
- `http_proxy` が設定された環境でも localhost がプロキシに吸われないよう、
  スクリプト内の `curl` は必ず `--noproxy '*'` を付けています。

---

## 11. 検証状況

スタブ環境（`/health` が 503→200 に変わる偽 `llama-server` と、サーバ到達を確認して
`results.json` を吐く偽 `llmbench`）で、対象解決・通し実行・gguf 不在・サーバ起動失敗・
スイート異常終了・実行中の SIGINT・resume・conf 上書き・seed 無効化の切り替わりを確認済み
（2026-08-29 / 15ケース）。

**実 `llama-server` と実 gguf を使った通し実行は未検証**です。初回は
`--list` → `--dry-run` → 量子化1つ + スイート1つ、の順で試してください。
