# 生成コードのインデント潰れ — 原因調査

対象: Qwopus3.8-27B-Flash / 自前 Q4_K_M / l6スイート60問
更新: 2026-09-05（条件A実施後）
自信度: **事象の特定＝HIGH** / **原因＝未特定（第一候補を棄却済み）**

## 結論（先に）

**低スコアの原因はモデルの実力ではなく、生成テキストのインデント潰れ。**
行頭空白がネスト深度に関係なく1スペースへ潰れ、`llmbench/patch.py` の
`ast.parse()` が `IndentationError` で落ち、`generated/` が空になって
**テスト実行前に0点が確定**する。

**投機デコード (`--spec-type draft-mtp`) は原因ではない。**
条件A（同一 gguf のまま投機のみOFF）で潰れは消えるどころか増えた。

| ラン | 投機 | 潰れ | resolved |
|---|---|---:|---:|
| `20260905_014833_mtp-Q4_K_M-l6` | ON | 15/60 (25.0%) | 44/60 = 73.3% |
| `20260905_023444_mtpoff-Q4_K_M-l6` | OFF | **34/60 (56.7%)** | — |

## 1. 事象

生出力の行頭空白が **深さに関係なくすべて1スペース**。
例（`vm.py`、本来 def→while→if の3階層）:

```
def run(program: list[tuple]):
 stack: list = []
 while ip < len(program):
 op = program[ip]
 if name == PUSH:
 stack.append(op[1])
```

## 2. 0点に至る経路（コード上で確認済み）

1. `llmbench/patch.py::_is_real_code()` が `.py` ブロックに `ast.parse()` を課す
2. 潰れた出力は `IndentationError` → ブロック不採用
3. `ParsedPatch.files` が空 → `TaskResult.parsed_files` が空
4. `runner.py::_write_artifacts()` が `generated/` に何も書かない
5. テスト以前に失敗確定

`generate_retries: 1` の再生成でも救えていない。

## 3. 検出方法

```bash
python3 tools/check_indent_collapse.py results/<stamp>_<label>_artifacts
```

潰れを1件でも検出すると終了コード1。ラン後のチェックにそのまま挟める。
判定は `patch.py` と同じ「先勝ち + 実コード判定」に合わせてあり、思考中の
断片ブロックが先に来ても誤検知しない。

| 判定 | 意味 |
|---|---|
| `ok` | 採用できるブロックがあり4スペース系 |
| `COLLAPSED` | 行頭が1スペースのみ + 構文エラー（これが事故） |
| `COLLAPSED-but-parses` | 1スペースのみだが平坦なので通った（潰れは起きている） |
| `MIXED` | 1スペースと4スペースが同一ブロックに混在 |
| `NO-PARSABLE-BLOCK` | python として通るブロックが1つも無い |
| `NO-CODE-BLOCK` | コードフェンスが無い（コーディング以外のスイートでは正常） |

## 4. 分かっていること

### 4.1 投機デコードは原因ではない（条件A、2026-09-05）

同一 gguf・同一パラメータで `SERVER_EXTRA_ARGS=""` にして再計測した結果、
潰れは 15/60 → **34/60 に増加**。llama.cpp
[#25618](https://github.com/ggml-org/llama.cpp/issues/25618)
（draft-mtp × Q4 で greedy 出力が乖離する既知バグ）を第一候補としていたが、
**棄却**する。

> ⚠ **交絡に注意**: 条件A は切り分けを速くするため `RUNS_L6=1` で回した。
> 元の mtp ランの `runs` が 1 でない場合、試行回数の差だけで潰れ率は動く
> （`generate_retries` と合わせて、試行が多いほど「通った1本」が残りやすい）。
> **両ランの `results.json` の `summary.runs` を突き合わせるまで、
> 「投機ONの方が潰れにくい」とは読まないこと。** 棄却できるのは
> 「投機が潰れの必要条件である」という主張だけで、これは runs に依らず成立する。

### 4.2 生成途中で切り替わる

条件A の t020 / t032 は同一ブロック内に 1スペース行と4スペース行が混在
（`[1sp=41 4sp=5]` / `[1sp=61 4sp=4]`）。
応答単位で書式が決まるのではなく、**生成の途中でトークンが入れ替わる**。

### 4.3 このモデル以外では起きていない

`results/` 配下の全 artifacts（36ラン）を検査したが、`COLLAPSED` が出たのは
Qwopus3.8-27B-Flash Q4_K_M の2ランのみ。glm-coding / opencode-go /
Qwen3.8-27B 系の過去ランはいずれも 0 件。

### 4.4 harness 側ではない

`raw_output` は `runner.py` で無変換のまま書き出されている。
同一ランの中で45件が4スペースを保持しており、転送や後処理の一律劣化ではない。

## 5. 残っている仮説

| # | 仮説 | 切り分け |
|---|---|---|
| **H1** | 自前 Q4_K_M の量子化（`token_embd` / `output` の低ビット化でトークン選択が壊れる） | 条件B: HF配布 Q5_K_M<br>条件C: ヘッドを Q8_0/F16 に引き上げ |
| **H2** | デトークナイズ / vocab 側（トークンIDは正しいが文字列化で潰れる） | `tools/probe_indent_tokens.py` |
| **H3** | モデル本体の癖（3.8 Flash 固有） | 条件B で Q5_K_M でも出れば該当 |
| **H4** | llama.cpp のビルド固有 | 別ビルド / 別バックエンドで同一 gguf |

## 6. 次にやること

### 6.1 まず H2 を潰す（サーバ1本・数分）

`tools/probe_indent_tokens.py` は同じプロンプトを N 回投げ、生成トークンID列を
1個ずつ `/detokenize` した結果の連結と、サーバが返した `content` を比較する。

```bash
python3 tools/probe_indent_tokens.py --url http://localhost:8085 -n 10 --show 12
```

- 連結 ≠ content → **デトークナイズ/集約の問題**（H2）。gguf の vocab と
  pre-tokenizer を確認する
- 連結 == content で行頭が単一スペーストークン → **モデル/量子化がそのトークンを
  選んでいる**（H1 / H3）。条件Bへ進む

### 6.2 条件B: HF配布 Q5_K_M

HF の Jackrong/Qwopus3.8-27B-Flash-GGUF が配布しているのは **Q5_K_S / Q5_K_M のみ**。
今回の Q4_K_M は自前量子化なので、配布版で潰れが出るかどうかで H1 と H3 が割れる。

### 6.3 条件C: ヘッドの精度を上げた Q4_K_M

`--output-tensor-type` / `--token-embedding-type` を Q8_0 か F16 にして再量子化。
H1 が当たりなら潰れが減る。

## 7. 復旧不能な点

潰れたタスクを「4スペースに直して再採点」することは**できない**。
全階層が1スペースに潰れておりネスト深度の情報が失われているため、
元のブロック構造を一意に復元できない。再計測が必要。

## 8. 恒久対策の提案（llmbench 側・未実装）

現状この事故はレポート上「モデルが解けなかった」と区別できない。
`n_truncated` / `n_refused` と同格で summary に立てるのが望ましい。

- `summary.n_parse_failed`（`parsed_files` が空だったタスク数）
- `summary.n_indent_collapsed`（1スペースのみで4スペース皆無）
- 0でないランは実力として読んではいけない旨をレポート冒頭に出す

## 付録: 条件A（投機OFF）で異常だった36件

`tools/check_indent_collapse.py` の「潰れ」カウント34件は `COLLAPSED` + `COLLAPSED-but-parses`。
`NO-PARSABLE-BLOCK` の2件は別枠だが、1スペース行が支配的なので同根とみてよい。

```
COLLAPSED (31):
  t002 t003 t006 t009 t011 t012 t013 t015 t018 t019 t021 t024 t025 t026
  t027 t030 t031 t033 t034 t036 t038 t039 t040 t045 t048 t049 t051 t054
  t056 t057 t059
COLLAPSED-but-parses (3): t004 t016 t017
NO-PARSABLE-BLOCK (2, 1sp/4sp 混在): t020 t032
```

**投機ONで潰れた15件（t003 t009 t011 t017 t018 t021 t024 t033 t034 t036
t039 t040 t045 t049 t059）は、すべて投機OFFでも潰れている。**
投機OFF側だけで潰れるタスクが21件上乗せされた形で、包含関係になっている。
投機を切っても事象がまったく減らない以上、投機は原因ではない。
