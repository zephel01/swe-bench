# 🤖 自動化ガイド — モデル追加からレポートまで

新しいモデル（あるいは同じモデルの別量子化）が手に入ってから、比較レポートを出すまでの
**一気通貫の手順**です。1回やれば終わりの作業ではなく、モデルが増えるたびに同じ順序で
繰り返すものとして書いています。

> 個々のコマンドの詳細は [USAGE.md](USAGE.md)、スイープの全オプションは [SWEEP.md](SWEEP.md)、
> gguf の読み方は [GGUF_PROBE.md](GGUF_PROBE.md) にあります。ここは**順序と判断**の文書です。

---

## 全体像

```
① 調べる      gguf_probe          載るか / MTP は使えるか / KV は何 KB/token か
      ↓
② 決める      probe (tok/s)       ctx・KV・MTP を変えて実測し、一番速い条件を選ぶ
      ↓
③ 固定する    tools/sweep.conf    全量子化で同じ条件になるように書く
      ↓
④ 回す        tools/sweep.sh      無人実行。落ちても次へ進み、再開できる
      ↓
⑤ 検証する    manifest / preflight  条件が本当に揃っていたかを確認する
      ↓
⑥ まとめる    compare / certify   比較レポートと「使えるライン」判定
```

**②を飛ばして④に行かないこと。** L6 は 60問 × runs 5 = 300生成です。条件が悪いまま回すと
半日が無駄になります。②は3条件でも5分で終わります。

---

## ① 調べる — `gguf_probe`

GPU を回す前に、ファイルを読むだけで決まることを確定させます。

```bash
cd ~/llm/apps/swe-bench && source .venv/bin/activate

for f in /llm/models/<モデル>-GGUF/*.gguf; do
  printf '=== %s\n' "$(basename "$f")"
  python gguf_probe.py "$f" | grep -iE "MTP/nextn|KVキャッシュ|context_length"
done
```

見るのは3つです。

| 出力 | 何が決まるか |
|---|---|
| `MTP/nextn テンソル: N 本` | `N > 0` なら `--spec-type draft-mtp` が使える（**速度が1.3〜2倍**） |
| `KVキャッシュ: N/M 層が保持 = X KB/token` | `--ctx-size` を上げたときの VRAM 増加量 |
| `native ctx` | `--ctx-size` の上限 |

> [!IMPORTANT]
> **KV の大きさを層数から推測しないこと。** ハイブリッド注意のモデルは、全層で KV を持つ
> 前提の計算と数倍ずれます。実例: `Qwen3.8-27B` は 65層のうち 17層だけがフル Attention で、
> KV は **68 KB/token**（ctx 65536 でも 4.25 GiB）。全層前提で見積もると 260 KB/token になり、
> 「載らない」と誤判断して不要に ctx を削ることになります。

> [!WARNING]
> **同じモデル名でもファイルによって MTP の有無が違うことがあります。**
> 実例: `Qwen3.8-27B-Uncensored` は MTP 4本、無印 `Qwen3.8-27B` は 0本でした。
> 量子化ごとに確認してください（`tools/sweep.sh` は起動前に自動判定しますが、
> **どの条件で測ったかを把握しておくのは人間の仕事**です）。

VRAM 予算から ctx を逆算したいときは `gguf_plan.py` が起動コマンドごと出します。

```bash
python gguf_probe.py --json --out gguf.json /llm/models/<モデル>-GGUF/*.gguf
python gguf_plan.py gguf.json --vram 31 --pick Q4_K_M
```

---

## ② 決める — 条件ごとに tok/s を実測する

ベンチを走らせる前に、**サーバ単体で** 1条件あたり1〜2分で測ります。`llmbench` は使いません。

```bash
LS=~/llm/apps/llama.cpp/build-cuda/bin/llama-server
M=/llm/models/<モデル>-GGUF/<モデル>-Q4_K_M.gguf

probe() {
  echo "=== $* ==="
  pkill -f "llama-server -m"; sleep 3
  "$LS" -m "$M" --host 127.0.0.1 --port 8085 -ngl 99 --parallel 1 \
     --batch-size 2048 --ubatch-size 512 -fa on --device CUDA0 "$@" \
     > /tmp/srv.log 2>&1 &
  local pid=$! waited=0
  until curl -sf --noproxy '*' localhost:8085/health >/dev/null; do
    if ! kill -0 $pid 2>/dev/null; then
      echo "  ❌ 起動に失敗。ログ末尾:"; tail -8 /tmp/srv.log; return 1
    fi
    if (( waited > 300 )); then echo "  ❌ 300秒たっても起動しません"; return 1; fi
    sleep 2; waited=$((waited+2))
  done
  echo -n "  VRAM: "; nvidia-smi --query-gpu=memory.used --format=csv,noheader
  for i in 1 2; do
    curl -s --noproxy '*' localhost:8085/completion -H 'Content-Type: application/json' \
      -d '{"prompt":"Write a Python function that merges two sorted lists.\n\n","n_predict":256,"temperature":0,"cache_prompt":false}' \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
t = d.get("timings")
print("  %.1f tok/s (%d tok)" % (t["predicted_per_second"], t["predicted_n"]) if t else "  timings なし")
'
  done
}

probe --ctx-size 32768 -ctk q8_0 -ctv q8_0        # KV を量子化して ctx を抑える
probe --ctx-size 65536                            # KV f16
probe --ctx-size 65536 --spec-type draft-mtp      # + MTP (①で 0本ならこれは飛ばす)
pkill -f "llama-server -m"
```

実測例（RTX 5090 32GB / `Qwen3.8-27B-Uncensored-Q4_K_M`）:

| 条件 | tok/s | VRAM |
|---|---|---|
| ctx 32768 / KV q8_0 | 73.7 | 17,164 MiB |
| ctx 65536 / KV f16 | 74.6 | 20,118 MiB |
| **+ `--spec-type draft-mtp`** | **136.3** | 21,210 MiB |

読み取れること:

- **KV の量子化は速度にほぼ効かない**（-1%）。VRAM が足りているなら f16 のままでよい
- **MTP は 1.84倍**。投機デコードは検証付きなので**出力は変わらず速度だけ上がる**
- 一番重い量子化（この例では Q6_K = 26,258 MiB）でも VRAM に収まるかを、ここで確認しておく

> [!TIP]
> 生成が短いと tok/s のブレが大きいので、2回測って安定していることを確認します。
> 1回目と2回目が大きく違う場合は、他のプロセスが GPU を使っている可能性があります。

---

## ③ 固定する — `tools/sweep.conf`

②で決めた条件を書きます。このファイルは `.gitignore` 済みなので実パスを書いて構いません。

```bash
cp tools/sweep.conf.example tools/sweep.conf
```

```sh
# 環境
MODEL_DIR=/llm/models/Qwen3.8-27B-GGUF
MODEL_PREFIX=Qwen3.8-27B
LLAMA_SERVER=/home/<user>/llm/apps/llama.cpp/build-cuda/bin/llama-server

# 対象量子化
QUANTS="Q4_K_M Q5_K_M Q6_K"

# スイート (やらないものは 0)
RUN_L6=1; RUNS_L6=5
RUN_L7=1; RUNS_L7=3
RUN_CULTURE=0
RUN_UNC=0

# ②で決めた条件 — 全量子化で同じにする
DEVICE=CUDA0
CTX=65536
KV_TYPE=
SERVER_EXTRA_ARGS="--spec-type draft-mtp"
```

確認してから回します。

```bash
tools/sweep.sh --list      # 対象 (量子化 × スイート) と解決されたパス
tools/sweep.sh --dry-run   # 実際に発行されるコマンド
```

`--dry-run` の出力で、次の3点を目で確認してください。

- `--ctx-size` と `-ctk` が意図どおりか
- `--spec-type draft-mtp` が載っているか（`MTP: yes` と出る）
- `config: ... [seed 無効化]` だけか（`max_tokens` の書き換えが出る場合は ctx を下げた影響）

---

## ④ 回す — 無人実行

L6 を runs 5 で3量子化なら **数時間〜十数時間**かかります。SSH が切れても続くように起動します。

```bash
cd ~/llm/apps/swe-bench && source .venv/bin/activate

# tmux (推奨。あとから画面に戻れる)
tmux new -s sweep
tools/sweep.sh
#   Ctrl-B D でデタッチ / tmux attach -t sweep で戻る

# または nohup
nohup tools/sweep.sh > _OUTPUTS/sweep/run.log 2>&1 &
tail -f _OUTPUTS/sweep/run.log
```

### 進んでいるかを確認する

止まって見えても、たいていは thinking モデルが1タスクを長考しているだけです。
**ベンチ側ではなくサーバ側を見る**のが確実です。

```bash
nvidia-smi                       # 使用率が上がっていれば生成中
curl -s --noproxy '*' localhost:8085/health
tail -f _OUTPUTS/sweep/logs/<実行ID>/<量子化>_server.log
```

`sweep.sh` が起動直後に出す `VRAM 合計:` がモデルサイズを大きく下回っていたら、
**GPU に載り切っていません**（CPU にこぼれて数十倍遅くなります）。警告も出ます。

### 中断と再開

- Ctrl-C / kill で止めても、trap が `llama-server` を停止します（VRAM は掴まれたままになりません）
- 再開は `tools/sweep.sh` をもう一度叩くだけ。`_OUTPUTS/sweep/sweep_state.tsv` に `ok` で
  残っている（量子化, スイート）は飛ばします
- **条件を変えたら state を外すこと**。古い条件の結果を飛ばしてしまい、混ざります

```bash
mv _OUTPUTS/sweep/sweep_state.tsv _OUTPUTS/sweep/sweep_state.tsv.old
```

---

## ⑤ 検証する — 条件が本当に揃っていたか

**比較が成立するのは推論条件が揃っているときだけ**です。レポートを書く前に必ず見ます。

```bash
column -t -s$'\t' _OUTPUTS/sweep/manifest_<実行ID>.tsv
```

```
quant    model_id                  n_ctx   vram_used_mib  vram_total_mib  mtp
Q4_K_M   Qwen3.8-27B-Q4_K_M.gguf   65536   21210          32607           yes
Q5_K_M   Qwen3.8-27B-Q5_K_M.gguf   65536   23400          32607           yes
Q6_K     Qwen3.8-27B-Q6_K.gguf     65536   26258          32607           yes
```

| 列 | 揃っていないと |
|---|---|
| `n_ctx` | プロンプトの入り方が変わる。**速度も品質も比較できない** |
| `mtp` | **tok/s は比較できない**（品質スコアは投機デコードでも変わらないので比較できる） |
| `vram_used_mib` | モデルサイズの半分未満なら CPU にこぼれている。その行の tok/s は無意味 |
| `model_id` | 意図した gguf がロードされていたか（`model: "auto"` の実際の解決結果） |

各ランの `preflight` 出力（`_OUTPUTS/sweep/logs/<実行ID>/<量子化>_<スイート>.log` の冒頭）も
確認します。`判定: FAIL` なら結果自体がありません。`WARN` は続行しますが、
**`seed` 未指定の WARN は `runs>1` のための意図的なもの**です（`sweep.sh` が外しています）。

---

## ⑥ まとめる — `compare` / `certify`

`sweep.sh` は最後にスイートごとの比較コマンドを出力します。そのまま貼れば横断レポートになります。

```bash
llmbench compare results/*_Q4_K_M-l6_results.json \
                 results/*_Q5_K_M-l6_results.json \
                 results/*_Q6_K-l6_results.json --name l6_by_quant

# 「使えるライン」判定。分割実行した結果は --merge で1つに
llmbench certify --config config.yaml \
  results/*_Q4_K_M-l6_results.json results/*_Q4_K_M-l7_results.json --merge
```

`compare` は推論条件（量子化 / -ngl / n_ctx / 並列）が揃っているかを自動判定し、
ずれていれば「⚠️ 推論条件が揃っていません」と名指しで警告します。⑤で確認した
manifest と合わせて、レポートに条件を明記してください。

---

## 詰まったときの早見表

実運用で踏んだものを順に並べています。

| 症状 | 原因 | 対処 |
|---|---|---|
| preflight の後、画面が何も出ない | thinking モデルが長考中。多くの場合**止まっていない** | `nvidia-smi` と server.log を見る。1タスク数分〜十数分は正常 |
| 本当に遅い（数十倍） | モデル + KV が VRAM に収まらず CPU にこぼれた。**ログには何も出ない** | 起動直後の `VRAM 合計:` を確認。`--ctx-size` を下げるか `KV_TYPE=q8_0` |
| `max_tokens N が n_ctx M 以上です` で preflight FAIL | `config.yaml` の `max_tokens` が固定値のまま ctx を下げた | `ADJUST_MAX_TOKENS=1`（既定）が自動で下げる。手で直すなら ctx の 3/4 |
| `context type MTP requested but model doesn't contain MTP layers` | その gguf に MTP が無い | `MTP_AUTO=1`（既定）が自動で外す。①で有無を把握しておく |
| 量子化によって tok/s が倍違う | `mtp` 列が混ざっている | manifest を確認。tok/s の比較は同じ `mtp` の行同士でのみ |
| 途中まで走った結果が飛ばされる | `sweep_state.tsv` に前回の `ok` が残っている | 条件を変えたら state を退避する |
| `llama-server` が残って VRAM を掴んだまま | 強制終了などで trap が走らなかった | `pkill -f "llama-server -m"` |
| ポートが使用中で起動しない | 前のサーバが残っている | `tools/sweep.sh --force-port` |

---

## チェックリスト

長いランを始める前に、これだけ確認すれば事故はほぼ防げます。

- [ ] ① 全量子化で `gguf_probe` を通した（MTP の有無・KV KB/token・native ctx）
- [ ] ② 3条件の tok/s を実測し、**一番重い量子化でも VRAM に収まる**ことを確認した
- [ ] ③ `tools/sweep.conf` に条件を書き、`--list` と `--dry-run` で確認した
- [ ] ③ スイートと runs が意図どおり（`RUN_*` / `RUNS_*`）
- [ ] ④ 条件を変えたので `sweep_state.tsv` を退避した
- [ ] ④ tmux か nohup で起動した
- [ ] ⑤ 最初の1量子化が始まったところで `VRAM 合計:` と `MTP:` と `n_ctx` を目視した
- [ ] ⑥ レポートに推論条件（量子化 / ctx / KV / MTP / GPU）を明記した

---

## 関連ドキュメント

| 目的 | 読むもの |
|---|---|
| スイープの全オプション・出力・resume | [🔁 SWEEP.md](SWEEP.md) |
| gguf から ctx・KV・MTP を読む | [🔍 GGUF_PROBE.md](GGUF_PROBE.md) |
| `run` / `compare` / `certify` の詳細 | [📘 USAGE.md](USAGE.md) |
| `results.json` の仕様・他システム連携・CI | [🛠️ MANUAL.md](MANUAL.md) |
