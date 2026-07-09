# 🧩 タスク仕様書 — t001〜t040 (+ L6 architect t041〜t060 / L7 grandmaster t061〜t100)

各タスクが**何を調査しているか**(LLMのどの能力を測るか)と**採点基準**の一覧。

## 共通の採点フロー

全タスク同一のパイプラインで採点される:

1. **入力**: issue (バグレポート) + `buggy_code/` の全ソースをLLMに渡す (`tests/` は渡さない)
2. **機能評価 (resolved)**: 出力patchを一時コピーに適用 → 隠しpytestが**全件pass**で `resolved=1`、それ以外は `0`
   - FAIL要因: ①出力フォーマット不正でパース失敗 ②テスト失敗 ③タイムアウト(既定120秒)
3. **品質評価 (quality 0-100)**: 変更ファイルのみ対象
   - **Ruff** (重み0.4): `score = max(0, 100 − 8 × issue数/100行)` 対象ルール E/F/W/B/SIM/C4/S
   - **radon** (重み0.3): Maintainability Index (0-100) から最悪CCランクで減点 (A:0 / B:5 / C:15 / D:30 / E:45 / F:60)
   - **LLMレビュー** (重み0.3・任意): 別LLMの0-10点 × 10。無効時は残りで再正規化
4. **複合スコア**: `combined = resolved × (50 + 0.5 × quality)`

> 共通の品質落とし穴: 「全ファイル出力」指示に対し**無関係ファイルまで書き換える**・**不要なリファクタ**をすると、品質スコア低下や regression によるテスト失敗を招く。

## 一覧

| ID | タスク | 難易度 | バグ分類 | 主な調査対象 |
|---|---|---|---|---|
| t001 | sum_range | easy | off-by-one | 境界値の基本理解 |
| t002 | clamp | easy | 戻り値の取り違え | 分岐ロジックの最小修正 |
| t003 | tags | easy | mutable default引数 | Python特有の罠の知識 |
| t004 | palindrome | easy | 仕様未実装 | docstring仕様とコードの乖離検出 |
| t005 | stats | easy | エッジケース未処理 | 空入力ハンドリング |
| t006 | calendar_utils | medium | ドメインルール誤実装 | 暦の知識+複合条件+波及効果 |
| t007 | word_freq | medium | 正規化漏れ | 仕様準拠の文字列処理 |
| t008 | search | medium | 返り値契約違反 | アルゴリズムの契約理解 |
| t009 | fib | medium | 基底条件のずれ | 再帰+メモ化の理解 |
| t010 | csv_line | medium | 機能丸ごと欠落 | 状態機械の新規実装力 |
| t011 | lru | hard | 退避方向の逆転 | ステートフルなデータ構造 |
| t012 | cart | hard | 意味論の取り違え | 複数ファイルでのバグ局所化 |
| t013 | ratelimit | hard | 境界条件 (≤ vs <) | ヒントからの原因絞り込み |
| t014 | scheduler | hard | min/maxヒープ逆転 | 制約付き修正 (FIFO維持) |
| t015 | confmerge | hard | shallow merge | 再帰実装+非破壊性 |

---

## Easy — 1行修正で直る基本バグ

### t001 sum_range — off-by-one

- **バグ**: `range(1, n)` で末尾が合計に入らない (`sum_to_n(10)` → 45)
- **期待修正**: `range(1, n + 1)`
- **調査内容**: Pythonの`range`排他的終端という最頻出バグの即時特定。これに落ちるモデルは実用以前
- **テスト**: n=10 (基本) / n=1 / **n=0 (エッジ)** / n=100
- **落とし穴**: `n*(n+1)//2` への書き換え自体は正解だが、issueは「最後の数が含まれない」と原因を示しており、最小修正からの逸脱はLLMレビュー採点で減点対象

### t002 clamp — 戻り値の取り違え

- **バグ**: `value < low` のとき `high` を返す
- **期待修正**: `return low`
- **調査内容**: issueの再現条件 (`clamp(-5,0,10)`→10) から該当分岐を特定する最小デバッグ能力
- **テスト**: 下限超過 / 上限超過 / 範囲内 / **境界値ちょうど (0と10)**

### t003 tags — mutable default引数

- **バグ**: `def add_tag(tag, tags=[])` — デフォルトリストが呼び出し間で共有される
- **期待修正**: `tags=None` + `if tags is None: tags = []`
- **調査内容**: Python特有の落とし穴の知識。「状態がリークする」という症状記述から原因に到達できるか
- **テスト**: 連続呼び出しでリークしない / **明示的にリストを渡した場合のin-place動作を維持** (後者を壊す過剰修正を検出)

### t004 palindrome — 仕様未実装

- **バグ**: docstringは「大文字小文字・空白・記号を無視」と言うが `text == text[::-1]` のみ
- **期待修正**: `isalnum()`フィルタ + `lower()` で正規化してから比較
- **調査内容**: ドキュメント(仕様)とコードの乖離を読み取り、欠けたロジックを補完する力
- **テスト**: "A man, a plan, a canal: Panama" / 単純回文 / 非回文 / **空文字列**

### t005 stats — エッジケース未処理

- **バグ**: `average([])` が ZeroDivisionError
- **期待修正**: 空チェックで `0.0` を返す (docstringに明記済み)
- **調査内容**: 例外を握りつぶす(`try/except: return 0.0`)のではなく、明示的な事前条件チェックを書くか — 品質スコアで差が出やすい
- **テスト**: 空リスト→0.0 / 整数平均 / float精度

## Medium — 原因特定に1段階の推論が必要

### t006 calendar_utils — グレゴリオ暦ルール

- **バグ**: `is_leap_year` が `year % 4 == 0` のみ (1900を閏年と誤判定)
- **期待修正**: 400年例外 → 100年例外 → 4年ルールの3段判定
- **調査内容**: ①ドメイン知識(暦) ②バグが`days_in_month`に**波及**していることの理解 (修正はis_leap_yearのみでよい、という判断も含む)
- **テスト**: 1900/2100 (世紀年・非閏年) / 2000/1600 (400年・閏年) / 通常年 / **days_in_month(1900,2)==28 の波及確認** / 他の月

### t007 word_freq — 正規化漏れ

- **バグ**: 大文字小文字区別+句読点が残る ("Dog"/"dog"/"DOG." が別キー)
- **期待修正**: `strip(string.punctuation)` + `lower()`、空になった語はスキップ
- **調査内容**: 仕様準拠の文字列正規化。既存のdict集計構造を保ったまま直せるか
- **テスト**: 大小混在 / 句読点付き / 空文字列 / **記号のみのトークン ("..." が空キーにならないか)**

### t008 search — 返り値契約違反

- **バグ**: 二分探索が「見つからない」とき `-1` でなく挿入位置 (`lo`) を返す
- **期待修正**: `return lo` → `return -1` (探索ループ自体は正しい)
- **調査内容**: アルゴリズム本体は正しいと見抜き、**契約(返り値仕様)違反だけ**を直せるか。ループを書き直して無限ループや境界バグを混入させないか
- **テスト**: 中間欠損 ([1,3,5]の2) / 両端欠損 / **全要素のインデックス一致 (探索本体のregression検出)** / 空リスト

### t009 fib — 基底条件のずれ

- **バグ**: 基底が `n <= 2: return n` (fib(2)=2になる)
- **期待修正**: `n <= 1: return n`
- **調査内容**: 「fib(2)以降すべてずれる」という症状から再帰の基底条件に到達する力。メモ化構造の維持
- **テスト**: 基底3値 / 数列11項の完全一致 / **fib(30)=832040 (性能=メモ化が壊れていないか)**

### t010 csv_line — 機能丸ごと欠落

- **バグ**: `line.split(",")` のみで引用符サポートが未実装
- **期待修正**: 引用符の状態を持つループ (in_quotes) + `""`エスケープ処理
- **調査内容**: 1行修正では直らない**新規実装型**。仕様 (引用内カンマはリテラル、`""`は1文字) を満たす状態機械を書けるか。複雑度が上がりやすく radon/CCの品質差が最も出るタスク
- **テスト**: 平文 / 引用内カンマ / **`""`エスケープ** / 空フィールド / 単一フィールド

## Hard — 複数ファイル・状態・制約付き修正

### t011 lru — 退避方向の逆転

- **バグ**: `popitem(last=True)` で**最新**エントリを退避 (正: `last=False`)
- **期待修正**: 1引数の変更。`get`/`put`の`move_to_end`は正しいので触らない
- **調査内容**: OrderedDictのAPI意味論 (`last`の向き) と、アクセス履歴という**状態の推移**を追う力。症状 (「入れたばかりのキーが消える」) から退避方向の逆転を導けるか
- **テスト**: 退避順 (get後のput) / **putによる既存キーrefresh** / 容量上限 / capacity=0のValueError

### t012 cart — 複数ファイルでのバグ局所化

- **構成**: `discounts.py` (レート表・**正しい**) + `cart.py` (バグ)
- **バグ**: `subtotal() * rate` — 割引後合計でなく**割引額**を返す
- **期待修正**: `subtotal() * (1.0 - rate)`。discounts.pyは変更不要
- **調査内容**: ①2ファイルからバグのある方を特定 (issueに「レート表は正しい」とヒント) ②「10%オフ」の意味論 ③**正しいファイルを書き換えない**判断 — 余計な変更はregressionリスクと品質減点
- **テスト**: SAVE10で90.0 / コードなし / 未知コード / **小文字"half" (大文字小文字非依存の維持)** / 不正addのValueError

### t013 ratelimit — 境界条件

- **バグ**: `len(self._hits) <= self.max_requests` で上限+1回許可
- **期待修正**: `<` に変更
- **調査内容**: issueが「ウィンドウ失効処理は正しい」と探索範囲を限定している。ヒントを活用して`<=`/`<`の1文字に絞り込めるか。purgeロジックを書き直して時刻境界を壊さないか
- **テスト**: max=3で4回目拒否 / **ウィンドウ失効後の再許可 (purge側のregression検出)** / pending件数 / 不正引数

### t014 scheduler — 制約付き修正

- **構成**: `pq.py` (優先度キュー・バグ) + `scheduler.py` (利用側・**正しい**)
- **バグ**: heapqのmin-heapに `(priority, count, item)` をそのまま積み、低優先度が先に出る
- **期待修正**: `(-priority, count, item)` で符号反転。countによるFIFO tie-breakは**維持**
- **調査内容**: ①利用側でなくキュー側と特定 ②min-heapでmax優先度を実現するイディオム ③「同点時FIFOは現在動いており壊すな」という**明示的制約の遵守** (countまで反転させたら違反)
- **テスト**: 優先度降順 / **同点3件のFIFO維持** / 混合ケース / 空pop時のIndexError

### t015 confmerge — 再帰+非破壊性

- **構成**: `defaults.py` (デフォルト設定・**正しい**) + `confmerge.py` (バグ)
- **バグ**: `dict.update()` によるshallow mergeでネスト先の兄弟キーが消える
- **期待修正**: dict同士のみ再帰マージ、非dict (リスト含む) は置換、入力は非破壊
- **調査内容**: 3つの仕様を同時に満たす再帰実装: ①深いマージ ②**リストはマージでなく置換** ③**入力をmutateしない** (deepcopyせず`dict(base)`+再帰で両立できるか)
- **テスト**: 兄弟キー保持 / 2段ネストのマージ / リスト置換 / **入力の非mutation (snapshot比較)** / 新キー追加

---

## L4 expert (t021〜t032) — 仕様の細部理解・アルゴリズム正確性

天井効果を破る難問tier。**issueは症状ベース**(失敗例のみ・修正手順を書かない)で、
原因の診断を要求する。全タスク stdlib-only・gold全緑/buggy赤・ruff 0件。

| ID | テーマ | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t021 money | Decimal会計 | 銀行家の丸め→half-up | 丸め規約・仕様読解 |
| t022 interval | 整数閉区間集合 | 隣接マージの±1欠落 | 境界条件 (off-by-one) |
| t023 semver | SemVer比較 | プレリリース優先順位の逆転 | 仕様準拠の比較 |
| t024 lru_ttl | TTL付きLRU | 失効判定 `>` vs `>=` | 時間境界・状態管理 |
| t025 csv_rfc | RFC4180パーサ | `""` エスケープ未処理 | 状態機械 |
| t026 topo | トポロジカルソート | 循環検出の欠落 | アルゴリズム契約 |
| t027 coins | 最小硬貨枚数 | 貪欲法 (非正準で非最適) | DP vs 貪欲の判別 |
| t028 backoff | 指数バックオフ | 指数の off-by-one | 数式・初期条件 |
| t029 wrap | 表示幅折返し | 全角を幅1で計算 | Unicode幅・国際化 |
| t030 json | JSON再帰下降 | `\uXXXX` 未デコード | エスケープ処理 |
| t031 graph | 禁止辺つき最短経路 | 禁止辺チェック欠落 | 制約付き探索 |
| t032 interpreter | 式評価器 | `**` を左結合化 | 演算子結合性・パーサ |

## L5 frontier (t033〜t040) — 複数ファイル・回帰罠・性能制約

リポジトリ風の難所。`tests/` を `test_core.py`(既存挙動をロック=回帰罠) と
`test_bug.py`(バグを捕捉) に分離。t035/t037/t039/t040 は **2つの結合バグ**を内包し、
片方だけ直しても別テストが落ちる。t039/t040 は `perf_timeout` + 10万件 perf テスト付き。

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t033 kvstore | journal.py + store.py | 内側commitが親へ引き継がず外側rollback不能 | ネストTx |
| t034 pubsub | events.py + bus.py | 配信中に解除した購読を呼ぶ | 配信中の状態変化 |
| t035 template | lexer/renderer/helpers | ①出力非エスケープ ②forスコープ漏れ | autoescape・スコープ |
| t036 query | builder.py + dialect.py | where_in が値を非パラメータ化 | インジェクション安全 |
| t037 di | container.py | ①singleton非キャッシュ ②例外後にresolving汚染 | ライフサイクル管理 |
| t038 markdown | inline.py + blocks.py | 連続箇条書きを1つの<ul>にまとめない | ブロック状態機械 |
| t039 ratelimit_sw | limiter.py | ①退避境界 ②上限の二重境界 | 境界 + 性能制約 |
| t040 vm | opcodes.py + vm.py | ①SUBオペランド順 ②JZ条件反転 | バイトコード解釈 + 性能 |

> 既存 t016〜t020 (hard) は README / `llmbench list-tasks` を参照。

---

## L6 architect (t041〜t060) — 任意オプション `--with-l6` / 単体実行 `--only-l6`

上位帯(27B〜35B級)の天井効果を破るための**追加20問**。既定の40問評価には含まれず、
別台帳 `tasks/tasks_l6.jsonl` に置かれ、`--with-l6` 指定時のみ評価される
(`difficulty=architect` → certify では **L6**)。全問「issueは症状のみ・原因と修正範囲は
モデルに委ねる」設計で、`test_core.py`(回帰罠) と `test_bug.py`(バグ捕捉)、一部に
`test_perf.py`(perf_timeout) を持つ。既定40問を除いて L6 だけを実行したい場合は
`--only-l6` を使う（分割運用向け。後日 `certify --merge` で既定40問の結果と統合可）。

### 複数ファイル・リポ規模 (t041〜t048)

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t041 config_loader | defaults/loader/validate | merge順でenv overrideが既定に潰される | 複数モジュールの実行順追跡 |
| t042 query_builder | query.py + dialect.py | PG方言でプレースホルダ($1..)未生成 | 抽象境界をまたぐ契約 |
| t043 event_sourcing | store/projection/replay | snapshot offset無視で二重計上・非冪等 | 状態復元の不変条件 |
| t044 plugin_loader | registry.py + loader.py | 循環未検出・解決順が登録順依存 | グラフ依存解決+順序非依存 |
| t045 cache_layer | cache/backend/serializer | 期限境界(<)で期限切れを返す・退避漏れ | レイヤ間の責務配置 |
| t046 di_scopes | container.py + scopes.py | singleton/request/transientを区別せず生成 | ライフタイム管理 |
| t047 migration_runner | runner.py + graph.py | 適用記録が非原子的で後続を誤適用扱い | 部分失敗時の整合性 |
| t048 http_router | router.py + params.py | 型変換なし・ワイルドカードが具体ルートを覆う | ルーティング優先規則+型 |

### 非機能要件 (t049〜t054) — `perf_timeout` 系

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t049 dedup_perf | dedup.py | `in list` で O(n²) | 計算量の意識 |
| t050 counter_race | counter.py | 非アトミックな read-modify-write | 並行時の不変条件 |
| t051 async_semaphore | pool.py | 例外経路で release 漏れ→枯渇 | 例外安全な資源管理 |
| t052 threadsafe_lru | lru.py | 容量off-by-one・ロック無し | データ構造+並行性 |
| t053 html_escape_ctx | render.py | 属性文脈のエスケープ欠如(XSS) | セキュリティの文脈依存 |
| t054 sql_param_nested | builder.py | ネスト条件で値を文字列補間 | 再帰構造の安全な走査 |

### 曖昧な仕様 (t055〜t058)

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t055 nl_date | nldate.py | 相対表現(next/in N days/週境界)未実装 | 曖昧仕様からの意図抽出 |
| t056 config_merge | merge.py | 浅いupdateでネスト/リスト規則が未分化 | 規則の階層的適用 |
| t057 csv_dialect | sniff.py | 区切りカンマ固定・クオート無視 | 例示からの一般化(RFC4180) |
| t058 version_range | vrange.py | 等値のみ・caret/tilde/複合未実装 | ドメイン記法の意味論 |

### 罠・敵対ロジック (t059〜t060)

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t059 kahan_sum | fsum.py | 単純加算で桁落ち(補正なし) | 数値的安定性 |
| t060 unicode_eq | ueq.py | 正規化なしの単純比較 | ユニコードの落とし穴 |

> 検証は `python3 _OUTPUTS/llm-bench-hard-l6/scripts/selfcheck_l6.py` または
> `llmbench validate --with-l6 --tasks t041,...,t060`。selfcheck 20/20 PASS 済み。

---

## L7 grandmaster (t061〜t100) — 任意オプション `--with-l7` / 単体実行 `--only-l7`

L1〜L6 の60問が最上位帯 (27B dense級) にほぼ踏破され、**最上位2モデルの差が実質1問**まで
縮小した (L6較正で天井効果が再発)。これを解消するための**追加40問**。既定の40問評価にも
`--with-l6` にも含まれず、別台帳 `tasks/tasks_l7.jsonl` に置かれ `--with-l7` 指定時のみ評価
される (`--with-l6` と独立に併用可。`difficulty=grandmaster` → certify では **L7**)。位置づけは
「使えるラインの判定」ではなく、現行モデル群の**頭打ちを検出する天井評価帯**。既定40問(+L6)を
除いて L7 だけを実行したい場合は `--only-l7` を使う（`--only-l6 --only-l7` でL6+L7のみ計60問）。

**5軸 × 8問** で構成し、それぞれ *異なる失敗様式* を突く。全問 stdlib-only・issueは症状のみ
(原因と修正範囲はモデルに委ねる)・`test_core.py`(回帰罠) と `test_bug.py`(バグ捕捉) を持つ。
**隠密性基準** (buggy が `test_core` の回帰罠を必ず通過する＝一見正しく見えるバグのみ許容) を
grandmaster tier の必須要件として機械強制。t098 のみ `perf_timeout: 30`。gate は暫定
**pass@1 ≥ 0.35 かつ combined ≥ 55** (実モデル較正で確定、現時点は未較正)。

### 軸A 数値安定性 (t061〜t068) — 読んでも一見正しい数値解析の失敗

| ID | モジュール | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t061 welford_variance | spread.py | 一括 `E[x²]−E[x]²` が大オフセット(1e9)で桁落ちし分散が0に。Welford/二段平均が要る | 分散の条件数・数値的安定性 |
| t062 logsumexp | logsumexp.py | `log(sum(exp(x)))` が x=1000 でoverflow・x=−1000 でlog(0)。max-shift恒等式が要る | 桁あふれ回避 (log-sum-exp) |
| t063 quadratic_roots | roots.py | `(−b±√D)/2a` は \|b\| 支配時に小根が桁落ちで消失。符号安定形が要る | 桁落ち(cancellation)回避 |
| t064 money_allocate | allocate.py | 比例配分を各自独立に丸め→合計が総額に一致しない(100を3分割で99)。最大剰余法(整数配分) | 丸め規約と総和保存 |
| t065 ema_bias | smoothing.py | ゼロ初期化EMAが空履歴を実サンプル0扱い→初期出力が0側にバイアス。adjust=True加重平均 | 初期化バイアスの認識 |
| t066 recurrence | recurrence.py | 前進漸化式 `E_n=1−n·E_{n−1}` が丸め誤差を n! 倍増幅→n≈20で巨大負値。Miller後退漸化式 | 漸化式の数値安定性 |
| t067 geometric_mean | geomean.py | 積を作ってから n乗根→inf/0 にover/underflow。log域 `exp(mean(log x))` | 対数域変換 |
| t068 haversine | geo.py | 球面余弦 `acos` が引数1近傍で精度全損→近接点が距離0(域外例外も)。半角(haversine)+atan2 | 近傍条件数・公式選択 |

### 軸B 状態一貫性 (t069〜t076) — 長い操作列と部分失敗で崩れる不変条件

| ID | 構成 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t069 saga_compensation | resources.py + saga.py | 補償の失敗を隔離せず伝播→逆順の先行ステップ解放を飛ばし原因誤差も隠す。回復経路も耐障害に | saga補償の部分失敗耐性 |
| t070 nested_txn_kv | store.py | ネストtxのcommitが子のundoログを親へ継がず→後の親rollbackで子が入れたキーを戻せない | ネストTx savepoint・undo継承 |
| t071 wal_replay | wal.py + recover.py | 単一パス回復が任意commitで全pendingをflush→未commitの割り込みtxが適用され後続は破棄 | WALリプレイの整合(交錯tx) |
| t072 undo_redo | commands.py + history.py | 単一コマンドapplyが `redo.clear()` 漏れ→undo後の編集でredo枝が生存し復活 | 線形履歴の枝切り(undo-redo分岐) |
| t073 inventory_reservation | inventory.py | confirm が active判定を落とし失効済み予約を確定→reserved二重減算(負値)・幻の在庫控除 | 予約期限×確定の不変条件 |
| t074 reorder_buffer | envelope.py + processor.py | `seq≥next` を並べて適用しギャップを飛ばす→遅れて来たseqが「過去」で破棄(順序違反) | 順序再構築(連続prefix) |
| t075 state_machine | transitions.py + machine.py | 副作用の前に状態/履歴を進める→副作用失敗で状態だけ前進し不正な後続遷移を許す | 前進遷移の部分失敗補償 |
| t076 optimistic_lock | store.py | `commit_all` が検証と適用を同一ループ→後のキー衝突で先行キーは適用・版上げ済み(非原子) | 複数キーCASの全か無か |

### 軸C 複数結合バグ (t077〜t084) — 各2バグを別ファイルに分散、部分修正は不合格

各タスクは *異なる能力軸* の独立バグを2個内包し、`test_bug` が各バグと1対1の直交テストを持つ。
**buggy の `.py` を1つだけ gold へ差し替えた中間版でも必ず `test_bug` が赤**になる (=片方修正では
通らない)。`scripts/verify_axis_c.py` がファイル差し替えを総当たりで自動検証済み。

| ID | 構成 | 仕込んだバグ (2件) | 主に測る力 |
|---|---|---|---|
| t077 job_scheduler | ordering.py + nextrun.py | ①同優先度タイブレークをLIFOにして投入と逆順 ②日次時刻をローカルtz変換せずUTCのまま→壁時計・日付ずれ | 順序安定性 + タイムゾーン日付 |
| t078 pagination | query.py + order.py | ①`filter→sort→slice` を `sort→slice→filter` 順にして行欠落 ②降順後の `reverse()` で同値タイ反転(安定崩れ) | フィルタ×オフセット順序 + 安定ソート |
| t079 serializer | encode.py + decode.py | ①区切り `\|` のエスケープ漏れで値が破損 ②bool復元を `bool(value)` にして `"False"` が True 化 | エスケープ漏れ + 型復元 |
| t080 cellref | colref.py + rangeexp.py | ①base26全単射で `divmod(n,26)` の1ずれ ②矩形展開が排他境界で最終行・最終列を落とす | 全単射変換 + 範囲展開境界 |
| t081 table_formatter | widths.py + render.py | ①列幅をヘッダ抜き(データ行のみ)で算出し最幅列で桁ずれ ②行を `rstrip()` せず末尾空白が残る | 列幅計算 + 整列(末尾空白) |
| t082 diffpatch | hunks.py + textio.py | ①下側コンテキスト窓を1行取りこぼす ②`splitlines()` で末尾改行情報を喪失 | コンテキスト境界 + 末尾改行 |
| t083 aggregate | groupby.py + stats.py | ①複合キーを文字列連結にして異なる組が衝突・併合 ②平均を整数除算 `//` で切り捨て | グループ化キー衝突 + 平均切り捨て |
| t084 cidr | mask.py + contains.py | ①ブロードキャストを `+2^host`(1つ先) ②所属判定を `<` にして端点(network/broadcast)を除外 | ネットマスク1ずれ + 所属境界 |

### 軸D 深い並行性 (t085〜t092) — 計装ゲートで決定的に捕捉する複合並行バグ

単発の並行タスク(t050/t051/t052)を超えた複合並行バグ。確率でなく**決定的**に捕捉するため、
テスト側でロック/フラグ/Conditionを計装オブジェクトへ差し替えインターリーブを強制する
(gold は決してハングしない)。全問 buggy 10/10 失敗・gold 10/10 緑を実測済み。

| ID | テーマ | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t085 lock_order | 送金 | `src→dst` 固定アドレス順取得→逆向き送金2本がAB/BAでデッドロック。id順(min→max)取得で循環排除 | ロック順序デッドロック |
| t086 lost_wakeup | 有界バッファ | 空判定を `while` でなく `if`→`notify_all` 横取り起床で2人目が空 `pop` の IndexError。再検査で再眠 | lost wakeup(条件再検査) |
| t087 dcl_init | 遅延シングルトン | None判定→生成をロックなし→並行初回で factory 二重実行。ロック後の二重チェック(DCL) | ダブルチェックロッキング |
| t088 cancel_leak | asyncio runner | 解放を `except Exception` のみ→`CancelledError`(BaseException)漏れで in_use/active リーク。try/finally | asyncキャンセル時の資源解放 |
| t089 toctou_pool | 資源プール | `_free[0]` の peek から remove まで無ロック→2スレッドが同一idを二重確保/ValueError。全体をロック | TOCTOU二重確保 |
| t090 future_double_set | 単一代入セル | `_done` 判定後の代入が無ロック→並行で両者が勝者(単一代入契約違反)。ロック内で判定+代入 | Future二重設定 |
| t091 gather_leak | asyncio.gather | gather のみで例外時に兄弟タスクを cancel せず走り続けリーク。finally で残タスク cancel | gather残タスクの後始末 |
| t092 rw_reentrant | reader-writerロック | writer待機中に同スレッドが再入readで書込優先ブロック→自分待ちデッドロック。スレッド毎read保持追跡で非ブロック再入 | reader-writer再入 |

### 軸E 敵対的パース・セキュリティ文脈・Unicode正規化 (t093〜t100)

L6 の t053/t057/t060 を深掘り。敵対入力下で不変条件(ディレクトリ内・単一ヘッダ行・単一script・
単一クエリ値・素のフィールド置換)を保ちつつ、危険に*見えるだけ*の正当入力を過剰拒否しない
**防御実装**を要求。共通の罠は演算順序(検査の前にデコード/正規化するか)と正規化回数。

| ID | 関数 | 仕込んだバグ | 主に測る力 |
|---|---|---|---|
| t093 path_canon | resolve_subpath | `..` 検査を完全デコード前に行い素の前置一致→二重エンコード・バックスラッシュ・全角traversal通過。NFKC→反復%デコード→`\`畳み→`base+sep` 前置要求 | 多層デコード後の封じ込め |
| t094 header_crlf | sanitize_header_value | CR/LFのみ拒否→`splitlines` が割る VT/FF/NEL(U+0085)/LS(U+2028)/PS(U+2029) 等を見逃す。改行集合全体+C0/DEL拒否(HTABは許可) | Unicode改行の網羅 |
| t095 confusable_label | is_allowed_label | 小さなキリル黒名簿で検知漏れ(ギリシャ等)かつ純キリルを過剰拒否。NFKC→字ごとにscript判定し非中立scriptを1つまで許可 | confusables/混在script |
| t096 nested_escape | render_search_link | href をHTMLエスケープのみでURL意味文字が生存(URLクエリ×HTML属性の入れ子)。内側%エンコード→外側HTML属性エスケープ(順序重要) | ネスト文脈エスケープ |
| t097 querystring | parse_query | 重複キー上書き+`%20` のみ対応で `+`→空白・一般%デコード欠落。`unquote_plus` で復号し重複を list 集積 | クエリRFC(+/%/重複) |
| t098 redos_path | is_valid_label_path | `^(\w+\.?)+$` の入れ子で指数バックトラック+末尾ドット許容。`^\w+(?:\.\w+)*$` で線形化。`perf_timeout:30`・28字+`!` を<1sで False | ReDoS(曖昧正規表現) |
| t099 tar_slip | safe_member_path | `normpath+startswith`(区切りなし)で prefix共有の兄弟通過・POSIXで `\` 生存。`\`畳み・絶対/ドライブ拒否・`dest+sep` 前置要求(FSアクセスなし) | tar-slip(アーカイブ脱出) |
| t100 format_inject | safe_format | `str.format` 直呼びで `{x.__class__…__globals__}`/`{obj[key]}` に到達。`Formatter().parse` で `.`/`[`/ネストフィールドを拒否 | format文字列注入 |

> 検証: `python3 _OUTPUTS/llm-bench-l7/scripts/selfcheck_l7.py`(gold緑/buggy赤/隠密性/ruff0 の
> 40/40 PASS)、`llmbench validate --with-l7`(mock-gold 40/40・mock-broken 40/40)、既存テスト23 passed。
> 各問のバグ本質は `tasks/tasks_l7.jsonl` と `_OUTPUTS/llm-bench-l7/design/axis_*.md` に対応。

---

## 設計意図のまとめ

| 観点 | 対応タスク |
|---|---|
| 1行修正の最小デバッグ | t001, t002, t008, t009, t011, t013 |
| 言語特有の罠 | t003 (mutable default), t011 (OrderedDict), t014 (heapq) |
| 仕様文からの実装補完 | t004, t007, t010, t015 |
| エッジケース設計 | t005, t001(n=0), t004(空), t007(記号のみ) |
| 複数ファイルのバグ局所化 + 無関係コード不変更 | t012, t014, t015, t033-t040, t041-t048, t069-t084 |
| 明示的制約の遵守 | t014 (FIFO維持), t015 (非破壊) |
| regression検出 (隠しテストが本体も再検証) | t008, t011, t012, t013, t033-t060 (test_core), t061-t100 (隠密性=test_core) |
| 仕様の細部理解・アルゴリズム正確性 | t021-t032 (expert) |
| 症状からの原因診断 (issueに修正手順なし) | t021-t100 |
| 複数の結合バグ (片方修正では通らない) | t035, t037, t039, t040, t077-t084 (各2バグ) |
| 性能制約 (perf_timeout) | t039, t040, t045, t049-t052, t059, t098 |
| リポジトリ規模の診断・設計判断 (architect) | t041-t060 (--with-l6) |
| 曖昧仕様からの意図抽出 / 敵対入力・数値安定性 | t055-t058 / t053, t059, t060 |
| 数値解析の失敗様式 (桁落ち・overflow・条件数) | t061-t068 (L7軸A) |
| 長い操作列・部分失敗での状態不変条件 | t069-t076 (L7軸B) |
| 決定的に捕捉する複合並行性 (デッドロック/競合/リーク) | t085-t092 (L7軸D) |
| 敵対的パース・セキュリティ文脈・Unicode正規化 | t093-t100 (L7軸E) |
| 天井評価帯 (grandmaster・現行モデル群の頭打ち検出) | t061-t100 (--with-l7) |

難易度が上がるほど「テストを通す」だけでなく「**正しい箇所だけを最小限に直す**」判断が要求され、機能スコアと品質スコアの乖離が観測しやすい構成になっている。
