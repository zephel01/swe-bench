# Qwopus3.8-27B-Flash Q4_K_M ベンチ低スコアの原因分析

対象ラン: `20260905_014833_mtp-Q4_K_M-l6`（60問 / artifacts のみ受領）
作成: 2026-09-05 / 自信度: **原因＝HIGH** / **引き金＝MODERATE**

## 結論（先に）

**モデルの実力低下ではない。生成テキストの行頭インデントが潰れて Python として
パースできず、60問中14問（23%）が採点前に0点化している。**
実際のロジック誤りは2問だけ。

resolved = **44/60 = 73.3%**。潰れが無ければ最大 96.7% 相当のランだった。

---

## 1. 実測データ

`llm_output.txt`（LLM生出力）と `generated/` を全60タスク突き合わせた結果。

| 区分 | 件数 | 内訳 |
|---|---:|---|
| テスト全通過 | 44 | 正常 |
| テスト失敗 | 2 | t046（dict をキーに使用 → `TypeError: unhashable type`）<br>t047（rollback 後に適用済みが残り `['a','a','b','c']`） |
| `generated/` が空 | **14** | t003, t009, t011, t018, t021, t024, t033, t034,<br>t036, t039, t040, t045, t049, t059 |

判定は `tools/check_indent_collapse.py` で再現できる（潰れを1件でも検出すると
終了コード1を返すので、ラン後のチェックにそのまま挟める）。

```
---- 60件: ok=45, COLLAPSED=14, COLLAPSED-but-parses=1
⚠ インデント潰れ 15/60 (25.0%)。投機デコード (--spec-type draft-mtp) と
  量子化の組み合わせを疑うこと。docs/MTP_INDENT_COLLAPSE.md 参照
```

## 2. 何が起きているか

14問の生出力は、行頭空白が **ネスト深度に関係なくすべて1スペース** になっている。
例（t040 `vm.py`、本来 def→while→if の3階層）:

```
def run(program: list[tuple]):
 stack: list = []
 ip = 0
 while ip < len(program):
 op = program[ip]
 name = op[0]
 if name == PUSH:
 stack.append(op[1])
```

## 3. 0点に至る経路（コード上で確認済み）

1. `llmbench/patch.py` の `_is_real_code()` が `.py` ブロックに `ast.parse()` を課す
2. 潰れた出力は `IndentationError` → ブロック不採用
3. `ParsedPatch.files` が空 → `TaskResult.parsed_files` が空
4. `runner.py::_write_artifacts()` が `generated/` に何も書かない（= NOGEN）
5. テスト以前に失敗確定

14問すべてで `ast.parse()` の例外を再現確認済み（`expected an indented block after
function definition / 'if' / 'while' / 'for'`）。

## 4. 潰れの性質（原因の切り分けに効く4点）

| # | 観測 | 含意 |
|---|---|---|
| 1 | **ファイル単位で完全に二値**。45件は全行4スペース、15件は全行1スペース。同一ファイル内の混在はゼロ | 行単位のランダムノイズではない。応答単位で経路が切り替わっている |
| 2 | **深さに関係なく一律1スペース**（深さ3も1スペース）。階層情報そのものが消えている | モデルが「1段=1スペース」で書いたのではない。**複数スペースのトークンが単一スペーストークンに置換**されている挙動 |
| 3 | t017 は潰れているが**ネストが無いため構文が通り合格**している | 潰れは合格側にも起きうる。表面化しないだけで発生率は 15/60 = 25% |
| 4 | `config.yaml` の `generate_retries: 1` があるのに14問すべて再生成でも失敗 | 偶発事故ではなく**再現性のある決定的な破壊** |

## 5. 引き金の第一候補

**`--spec-type draft-mtp` × Q4_K_M**。llama.cpp に未解決の既知バグがあり症状が一致する。

> **ggml-org/llama.cpp Issue #25618** —
> draft-mtp / draft-dspark の投機デコードが、**Q4量子化ターゲット**で greedy 時に
> vanilla と出力が乖離する（本来 lossless のはず）。Q4_K_M で確認。
> **ngram 投機では起きない**。回避策は bf16 ターゲット or ngram 投機。**未修正**。
> https://github.com/ggml-org/llama.cpp/issues/25618

傍証:

- 実行ラベル `mtp-Q4_K_M-l6` = `tools/sweep.sh` の `LABEL_PREFIX=mtp` + Q4_K_M。
  `tools/sweep.conf` には `SERVER_EXTRA_ARGS="--spec-type draft-mtp"` の行がある。
- HF の Jackrong/Qwopus3.8-27B-Flash-GGUF の配布は **Q5_K_S / Q5_K_M のみ**。
  Q4_K_M は自前量子化 = issue が指す Q4 領域そのもの。
- 前世代 **Qwopus3.6-27B-Coder-MTP-Q5_K_M** は 40問中38問クリア
  （`_OUTPUTS/llm-bench-hard/results_Qwopus27B.md`）。同系統・MTP 有り・**Q5** では
  この潰れが出ていない。
- 観測4（決定的に再現）は、issue が「greedy で決定的に乖離する」と言っているのと整合。

## 6. 対抗仮説（未排除）

| 仮説 | 切り分け |
|---|---|
| B. 自前 Q4_K_M で MTP ヘッド / output / token_embd まで低ビット化され、ドラフトが壊れている | 条件C（ヘッドを Q8_0/F16 に引き上げ） |
| C. Q4_K_M そのものの劣化（投機無関係） | 条件A で潰れが残れば該当 |
| D. モデル固有（3.8 Flash の癖） | 条件B（HF配布 Q5_K_M）で潰れが出れば該当 |

harness 側・tar 転送側の可能性は排除済み（同一 tar 内で45件は4スペースを保持、
`raw_output` は `runner.py` で無変換のまま書き出し）。

## 7. 切り分け手順

**同一 gguf・同一パラメータで投機デコードだけ切る**のが最短。既存の
`sweep_mtp.conf` / `sweep_nomtp.conf` は**モデルファイルが違う**ため、
重み差と復号経路差が交絡して A の判定には使えない。`tools/make_mtpoff_conf.sh` で
`tools/sweep_mtpoff.conf` を生成すること。

```bash
# 条件A: MTP入り gguf のまま --spec-type draft-mtp を外す (最優先)
bash tools/make_mtpoff_conf.sh
./tools/sweep.sh -c tools/sweep_mtpoff.conf --dry-run   # --spec-type が消えているか目視
./tools/sweep.sh -c tools/sweep_mtpoff.conf

python3 tools/check_indent_collapse.py \
    results/*_mtpoff-Q4_K_M-l6_artifacts
```

| 条件 | 変える点 | COLLAPSED=0 なら |
|---|---|---|
| **A** | draft-mtp を外す（Q4_K_M・同一gguf） | **投機デコード起因で確定**（B/C不要） |
| B | HF配布 Q5_K_M ＋ draft-mtp | 量子化ビット起因 |
| C | Q4_K_M ＋ MTPヘッド/output/token_embd を Q8_0 or F16 | 自前量子化の作り方の問題 |

判定基準: **COLLAPSED 件数**（スコアではなく）。A で 14→0 なら因果は一意。

## 8. 未確認事項（要確認）

1. 実行時の `llama-server` 起動コマンド全文。NucBox 側
   `_OUTPUTS/sweep/logs/Q4_K_M_server.log` の冒頭に sweep.sh が記録している
   （`MTP: yes/no` 行と引数列）。**これを見れば draft-mtp が実際に付いていたか即断できる。**
   Mac 側の `tools/sweep.conf`（Aug 29 時点）では当該行がコメントアウトされたままなので、
   NucBox 側の conf が別物になっている可能性が高い。
2. `results/20260905_014833_mtp-Q4_K_M-l6_results.json` と `_report.md`。
   `runs` / `sample_temp` / `n_truncated` / `fail_reason` の分布を見たい。
   受領したのは artifacts のみ。
3. Q4_K_M gguf の作成条件（imatrix の有無、`--output-tensor-type` /
   `--token-embedding-type` の指定、MTP テンソルの型）。

## 9. 復旧不能な点

潰れた14問を「4スペースに直して再採点」することは**できない**。
全階層が1スペースに潰れており、ネスト深度の情報が出力から失われているため、
元のブロック構造を一意に復元できない。再計測が必要。

## 10. 恒久対策の提案（llmbench 側）

現状、この事故はレポート上「モデルが解けなかった」と区別できない。
`n_truncated` / `n_refused` と同じ扱いで、**パース不能を summary に立てる**のが望ましい。

- `summary.n_parse_failed`（`parsed_files` が空だったタスク数）を追加
- 併せて `n_indent_collapsed`（1スペースのみで4スペース皆無）を警告として出す
- 0でないランは「実力」として読んではいけない旨をレポート冒頭に出す
  （既存の `n_truncated` のコメント方針と同じ）

## 付録: 影響を受けた15タスク

| task | ファイル | 状態 | ast.parse |
|---|---|---|---|
| t003 | tags.py | NOGEN | IndentationError (line 10) |
| t009 | fib.py | NOGEN | IndentationError (line 7) |
| t011 | lru.py | NOGEN | IndentationError (line 10) |
| t017 | slug.py | 合格 | ok（ネスト無しのため通った） |
| t018 | registry.py | NOGEN | IndentationError (line 9) |
| t021 | money.py | NOGEN | IndentationError (line 26) |
| t024 | cache.py | NOGEN | IndentationError (line 10) |
| t033 | journal.py | NOGEN | IndentationError (line 10) |
| t034 | bus.py | NOGEN | IndentationError (line 10) |
| t036 | builder.py | NOGEN | IndentationError (line 10) |
| t039 | limiter.py | NOGEN | IndentationError (line 10) |
| t040 | vm.py | NOGEN | IndentationError (line 12) |
| t045 | cache.py | NOGEN | IndentationError (line 7) |
| t049 | dedup.py | NOGEN | IndentationError (line 3) |
| t059 | fsum.py | NOGEN | IndentationError (line 5) |

いずれも中身のロジックは（インデントを除けば）妥当に見える。
t021（banker's rounding + 最大剰余法）、t024（TTL+LRU）、t040（スタックマシン）など、
従来モデルが落としてきた難問も内容自体は書けている。
**スコアが測っているのはモデルの実力ではなく復号経路の健全性になっている。**
