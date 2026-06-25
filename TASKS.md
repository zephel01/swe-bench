# 🧩 タスク仕様書 — t001〜t040 (+ L6 architect t041〜t060)

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

## L6 architect (t041〜t060) — 任意オプション `--with-l6`

上位帯(27B〜35B級)の天井効果を破るための**追加20問**。既定の40問評価には含まれず、
別台帳 `tasks/tasks_l6.jsonl` に置かれ、`--with-l6` 指定時のみ評価される
(`difficulty=architect` → certify では **L6**)。全問「issueは症状のみ・原因と修正範囲は
モデルに委ねる」設計で、`test_core.py`(回帰罠) と `test_bug.py`(バグ捕捉)、一部に
`test_perf.py`(perf_timeout) を持つ。

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

## 設計意図のまとめ

| 観点 | 対応タスク |
|---|---|
| 1行修正の最小デバッグ | t001, t002, t008, t009, t011, t013 |
| 言語特有の罠 | t003 (mutable default), t011 (OrderedDict), t014 (heapq) |
| 仕様文からの実装補完 | t004, t007, t010, t015 |
| エッジケース設計 | t005, t001(n=0), t004(空), t007(記号のみ) |
| 複数ファイルのバグ局所化 + 無関係コード不変更 | t012, t014, t015, t033-t040, t041-t048 |
| 明示的制約の遵守 | t014 (FIFO維持), t015 (非破壊) |
| regression検出 (隠しテストが本体も再検証) | t008, t011, t012, t013, t033-t060 (test_core) |
| 仕様の細部理解・アルゴリズム正確性 | t021-t032 (expert) |
| 症状からの原因診断 (issueに修正手順なし) | t021-t060 |
| 複数の結合バグ (片方修正では通らない) | t035, t037, t039, t040 |
| 性能制約 (perf_timeout) | t039, t040, t045, t049-t052, t059 |
| リポジトリ規模の診断・設計判断 (architect) | t041-t060 (--with-l6) |
| 曖昧仕様からの意図抽出 / 敵対入力・数値安定性 | t055-t058 / t053, t059, t060 |

難易度が上がるほど「テストを通す」だけでなく「**正しい箇所だけを最小限に直す**」判断が要求され、機能スコアと品質スコアの乖離が観測しやすい構成になっている。
