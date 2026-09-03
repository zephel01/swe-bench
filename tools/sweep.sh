#!/usr/bin/env bash
# =============================================================================
#  llmbench 量子化スイープ  —  llama-server の起動 → ベンチ実行 → 停止 を自動化
#
#  1量子化ごとに llama-server を起動し、有効化したスイート (l6 / l7 / culture /
#  unc) を順に走らせ、サーバを落として次の量子化へ進む。
#
#  使い方:  cp tools/sweep.conf.example tools/sweep.conf   # 実パスを書く (git管理外)
#           tools/sweep.sh --list         # 実行対象を確認するだけ
#           tools/sweep.sh --dry-run      # コマンドを表示するだけ
#           tools/sweep.sh                # 本番
#  設定は下のブロック / tools/sweep.conf / 環境変数 / CLI の順で上書きされる。
#  詳細は docs/SWEEP.md
# =============================================================================

# =============================================================================
#  ◆ 設定 — ここだけ編集すればよい ◆
#    すべて ${VAR:-既定値} 形式。環境変数でも一時上書きできる:
#      RUNS_L7=5 RUN_CULTURE=0 ./sweep.sh
# =============================================================================

# ── パス ─────────────────────────────────────────────────────────────────
#   REPO_DIR の既定は「このスクリプトの1つ上のディレクトリ」。
#   tools/sweep.sh として置く限り、どこに clone しても書き換え不要。
_SWEEP_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(dirname "$_SWEEP_SELF_DIR")}"   # llmbench リポジトリ
#   ↓ 空のままなら REPO_DIR から導出する (設定ファイルで REPO_DIR を変えても追随する)。
#     個別に別の場所を指したいときだけ値を書く。
LLMBENCH="${LLMBENCH:-}"        # 既定: $REPO_DIR/.venv/bin/llmbench
CONFIG="${CONFIG:-}"            # 既定: $REPO_DIR/config.yaml
TASKS_DIR="${TASKS_DIR:-}"      # 既定: $REPO_DIR/tasks
OUT_ROOT="${OUT_ROOT:-}"        # 既定: $REPO_DIR/_OUTPUTS/sweep  (ログ/state/サマリ)
RESULTS_DIR="${RESULTS_DIR:-}"  # 既定: $REPO_DIR/results         (llmbench --output)
MODEL_KEY="${MODEL_KEY:-local-openai}"                  # config.yaml の models: キー
MODEL_DIR="${MODEL_DIR:-/llm/models/Qwen3.8-27B-GGUF}"  # gguf の置き場
MODEL_PREFIX="${MODEL_PREFIX:-Qwen3.8-27B}"             # <PREFIX>-<QUANT>.gguf
LABEL_PREFIX="${LABEL_PREFIX:-}"                        # 結果ラベル/state の接頭辞
LLAMA_SERVER="${LLAMA_SERVER:-llama-server}"            # llama-server のパス

# ── 対象量子化 ───────────────────────────────────────────────────────────
#   明示リスト … "Q4_K_M Q6_K Q8_0"  (スペース or カンマ区切り)
#   自動検出   … "auto"  → MODEL_DIR の *.gguf を全部 (ファイル名順)
QUANTS="${QUANTS:-Q4_K_M Q6_K Q8_0}"
QUANT_EXCLUDE="${QUANT_EXCLUDE:-}"      # auto時に除外する正規表現 (例: "UD-|Q8_0")

# ── スイート: やる/やらない・runs・引数 ──────────────────────────────────
#   RUN_* = 1 で実行、0 でスキップ。ARGS_* は llmbench run に渡す台帳フラグ。
RUN_L6="${RUN_L6:-1}"                                   # 既定40問 + L6(architect)20問
RUNS_L6="${RUNS_L6:-5}"
ARGS_L6="${ARGS_L6:---with-l6}"

RUN_L7="${RUN_L7:-1}"                                   # L7(grandmaster) 16問のみ
RUNS_L7="${RUNS_L7:-3}"
ARGS_L7="${ARGS_L7:---only-l7}"

RUN_CULTURE="${RUN_CULTURE:-1}"                         # 日本のネットミーム知識のみ
RUNS_CULTURE="${RUNS_CULTURE:-3}"
ARGS_CULTURE="${ARGS_CULTURE:---only-culture --lang ja}"

RUN_UNC="${RUN_UNC:-1}"                                 # over-refusal 検査のみ
RUNS_UNC="${RUNS_UNC:-3}"
ARGS_UNC="${ARGS_UNC:---only-unc}"

SUITE_ORDER="${SUITE_ORDER:-l6 l7 culture unc}"         # 実行順 (RUN_*=0 は飛ばす)

# ── llama-server 共通引数 ────────────────────────────────────────────────
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8085}"
NGL="${NGL:-99}"                        # -ngl
FLASH_ATTN="${FLASH_ATTN:-on}"          # -fa (空なら付けない)
CTX="${CTX:-65536}"                     # --ctx-size
PARALLEL="${PARALLEL:-1}"               # --parallel (llmbench --concurrency と揃える)
BATCH="${BATCH:-2048}"                  # --batch-size
UBATCH="${UBATCH:-512}"                 # --ubatch-size
KV_TYPE="${KV_TYPE:-}"                  # q8_0 等 → -ctk/-ctv (-fa on 必須)
DEVICE="${DEVICE:-}"                    # --device (例: CUDA0)
TENSOR_SPLIT="${TENSOR_SPLIT:-}"        # --tensor-split (例: 0.5,0.5)
SERVER_EXTRA_ARGS="${SERVER_EXTRA_ARGS:-}"   # 追加で渡したい引数
CONCURRENCY="${CONCURRENCY:-}"          # llmbench --concurrency (空=渡さない)

# ── 量子化ごとの上書き ───────────────────────────────────────────────────
#   変数名は OVERRIDE_<量子化名>。記号 . - は _ に置換する。
#   ここに書いた引数は共通引数の**後ろ**に付くので、同じ引数なら後勝ちで上書きされる。
OVERRIDE_Q4_K_M="${OVERRIDE_Q4_K_M:-}"
OVERRIDE_Q5_K_M="${OVERRIDE_Q5_K_M:-}"
OVERRIDE_Q6_K="${OVERRIDE_Q6_K:-}"       # 例: "--ctx-size 32768 -ctk q8_0 -ctv q8_0"
OVERRIDE_Q8_0="${OVERRIDE_Q8_0:-}"
OVERRIDE_UD_Q4_K_XL="${OVERRIDE_UD_Q4_K_XL:-}"
OVERRIDE_UD_Q5_K_XL="${OVERRIDE_UD_Q5_K_XL:-}"
OVERRIDE_UD_Q6_K_XL="${OVERRIDE_UD_Q6_K_XL:-}"

# ── 挙動 ─────────────────────────────────────────────────────────────────
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-900}"  # /health が通るまでの待ち上限(秒)
STOP_WAIT="${STOP_WAIT:-60}"             # SIGTERM 後の待ち(秒)。超えたら SIGKILL
VRAM_SETTLE="${VRAM_SETTLE:-10}"         # 次モデル起動前の待機(秒)
SUITE_TIMEOUT="${SUITE_TIMEOUT:-0}"      # 1スイートの上限(秒)。0=無制限
STRIP_SEED_FOR_MULTIRUN="${STRIP_SEED_FOR_MULTIRUN:-1}"
                                         # runs>1 のとき seed 行を無効化した一時
                                         # config を使う (元の config.yaml は触らない)
ADJUST_MAX_TOKENS="${ADJUST_MAX_TOKENS:-1}"
                                         # 1 で config の max_tokens を実効 ctx に
                                         # 合わせて下げる。max_tokens >= n_ctx は
                                         # preflight が FAIL にする (実効上限が
                                         # n_ctx − プロンプト長になり効かないため)
MAX_TOKENS="${MAX_TOKENS:-}"             # 空=自動 (実効 ctx の 3/4、上限は下の CAP)
MAX_TOKENS_CAP="${MAX_TOKENS_CAP:-49152}"  # thinking モデルでもこれ以上は要らない実測値
                                         # ※ 元の値より小さくするときだけ書き換える
                                         #   (ctx を上げても max_tokens は勝手に増やさない)
MTP_AUTO="${MTP_AUTO:-1}"                # 1 で MTP の有無を gguf から判定し、
                                         # MTP を持たないファイルでは
                                         # --spec-type draft-mtp を自動で外す
                                         # (付けたまま起動すると llama-server は
                                         #  "model doesn't contain MTP layers" で
                                         #  起動に失敗する)。0 で従来どおり素通し
MTP_DETECT="${MTP_DETECT:-auto}"         # auto = gguf_probe.py が使えればそれで判定し、
                                         # 駄目ならヘッダを grep する。
                                         # grep = 常に grep (gguf パッケージ不要)
MTP_SCAN_BYTES="${MTP_SCAN_BYTES:-33554432}"
                                         # MTP 判定でまず読む先頭バイト数 (既定 32MiB)。
                                         # テンソル名は gguf のヘッダにあるので通常はここで足りる
MTP_SCAN_MAX_BYTES="${MTP_SCAN_MAX_BYTES:-536870912}"
                                         # 上で見つからないときに読む範囲 (既定 512MiB)。
                                         # 語彙の大きいモデルはヘッダが 32MiB を超えることが
                                         # あるので、「無し」と判定する前にここまで確認する
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-0}"    # 1 で llmbench の preflight を省略
RESUME="${RESUME:-1}"                    # 1 で完了済み(quant,suite)をスキップ
DRY_RUN="${DRY_RUN:-0}"                  # 1 でコマンド表示のみ
FORCE_PORT="${FORCE_PORT:-0}"            # 1 で PORT を掴んでいる既存プロセスを落とす
KEEP_GOING="${KEEP_GOING:-1}"            # 1 で失敗しても次の量子化へ進む
SWEEP_CONF="${SWEEP_CONF:-}"             # 追加設定ファイル (plain な VAR=値 で上書き)

# =============================================================================
#  ◆ 設定ここまで。以下は編集不要 ◆
# =============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

# --- 設定ファイル -----------------------------------------------------------
#   優先順: -c で明示 > 環境変数 SWEEP_CONF > tools/sweep.conf > <repo>/sweep.conf
#   --no-conf を付けると自動読み込みを止め、このスクリプトの既定値だけで走る。
#   conf は plain な代入 (VAR=値) で上のブロックを上書きする。CLI オプションが最優先。
_argv=("$@")
_conf_explicit=""
_no_conf=0
for ((_i = 0; _i < ${#_argv[@]}; _i++)); do
  case "${_argv[$_i]}" in
    -c|--conf)  _conf_explicit="${_argv[$((_i + 1))]:-}" ;;
    --conf=*)   _conf_explicit="${_argv[$_i]#--conf=}" ;;
    --no-conf)  _no_conf=1 ;;
  esac
done

SWEEP_CONF_LOADED=""
if [[ "$_no_conf" != "1" ]]; then
  if [[ -n "$_conf_explicit" ]]; then
    [[ -f "$_conf_explicit" ]] || { echo "設定ファイルが無い: $_conf_explicit" >&2; exit 1; }
    SWEEP_CONF="$_conf_explicit"
  elif [[ -n "$SWEEP_CONF" ]]; then
    [[ -f "$SWEEP_CONF" ]] || { echo "設定ファイルが無い: $SWEEP_CONF" >&2; exit 1; }
  else
    for _c in "$_SWEEP_SELF_DIR/sweep.conf" "$REPO_DIR/sweep.conf"; do
      if [[ -f "$_c" ]]; then SWEEP_CONF="$_c"; break; fi
    done
  fi
  if [[ -n "$SWEEP_CONF" ]]; then
    # shellcheck disable=SC1090
    source "$SWEEP_CONF"
    SWEEP_CONF_LOADED="$SWEEP_CONF"
  fi
fi

# REPO_DIR 由来のパスは conf を読んだ**後**に確定させる。
# (conf で REPO_DIR だけ書き換えたときに、他のパスが古い REPO_DIR を指さないように)
: "${LLMBENCH:=$REPO_DIR/.venv/bin/llmbench}"
: "${CONFIG:=$REPO_DIR/config.yaml}"
: "${TASKS_DIR:=$REPO_DIR/tasks}"
: "${OUT_ROOT:=$REPO_DIR/_OUTPUTS/sweep}"
: "${RESULTS_DIR:=$REPO_DIR/results}"

usage() {
  cat <<EOF
使い方: $SCRIPT_NAME [オプション]

  -c, --conf FILE      設定ファイルを明示指定 (plain な VAR=値 で上書き)
      --no-conf        設定ファイルを読まない (スクリプト既定値だけで走る)
      --quants LIST    対象量子化 (カンマ/スペース区切り、"auto" 可)
      --suites LIST    実行スイート (例: l7,unc)。指定外は実行しない
      --skip LIST      指定スイートだけ外す (例: l6)
      --runs N         全スイートの --runs を N に上書き
      --ctx N          --ctx-size を N に上書き
      --port N         llama-server のポート
      --model-dir DIR  gguf の置き場
      --results DIR    llmbench --output の出力先
      --timeout SEC    1スイートの上限秒 (0=無制限)
      --skip-preflight llmbench の preflight を省略
      --no-resume      完了済みでも再実行する
      --resume         完了済み(quant,suite)をスキップ (既定)
      --force-port     ポートを掴んでいる既存プロセスを落としてから起動
      --stop-on-error  失敗したらそこで打ち切る (既定は次の量子化へ進む)
  -n, --dry-run        実行せずコマンドを表示
  -l, --list           実行対象を表示して終了
  -h, --help           この表示

設定ファイルは -c 省略時に次の順で探し、最初に見つかったものを読む:
  1. 環境変数 SWEEP_CONF
  2. <このスクリプトと同じディレクトリ>/sweep.conf   (= tools/sweep.conf)
  3. <リポジトリ>/sweep.conf

例:
  cp tools/sweep.conf.example tools/sweep.conf   # 実パスを書く (git 管理外)
  $SCRIPT_NAME --list
  $SCRIPT_NAME --quants Q4_K_M,Q6_K --suites l7,unc
  RUNS_L7=5 RUN_CULTURE=0 $SCRIPT_NAME

同じ量子化で別モデル (例: MTP 版 / 非MTP 版) を比較するときは、conf を
分けたうえで LABEL_PREFIX を設定する。結果ラベルが <接頭辞>-<量子化>-<スイート>
になり、resume 用の state も sweep_state_<接頭辞>.tsv に分かれるため、
片方の完走がもう片方を「完了済み」と誤判定することがなくなる:
  $SCRIPT_NAME -c tools/sweep_mtp.conf     # LABEL_PREFIX=mtp   → mtp-Q4_K_M-l6
  $SCRIPT_NAME -c tools/sweep_nomtp.conf   # LABEL_PREFIX=nomtp → nomtp-Q4_K_M-l6
EOF
}

# --- CLI (設定より優先) -----------------------------------------------------
CLI_SUITES=""
CLI_SKIP=""
CLI_RUNS=""
DO_LIST=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--conf)        shift 2 ;;
    --conf=*)         shift ;;
    --no-conf)        shift ;;
    --quants)         QUANTS="$2"; shift 2 ;;
    --quants=*)       QUANTS="${1#--quants=}"; shift ;;
    --suites)         CLI_SUITES="$2"; shift 2 ;;
    --suites=*)       CLI_SUITES="${1#--suites=}"; shift ;;
    --skip)           CLI_SKIP="$2"; shift 2 ;;
    --skip=*)         CLI_SKIP="${1#--skip=}"; shift ;;
    --runs)           CLI_RUNS="$2"; shift 2 ;;
    --runs=*)         CLI_RUNS="${1#--runs=}"; shift ;;
    --ctx)            CTX="$2"; shift 2 ;;
    --ctx=*)          CTX="${1#--ctx=}"; shift ;;
    --port)           PORT="$2"; shift 2 ;;
    --port=*)         PORT="${1#--port=}"; shift ;;
    --model-dir)      MODEL_DIR="$2"; shift 2 ;;
    --model-dir=*)    MODEL_DIR="${1#--model-dir=}"; shift ;;
    --results)        RESULTS_DIR="$2"; shift 2 ;;
    --results=*)      RESULTS_DIR="${1#--results=}"; shift ;;
    --timeout)        SUITE_TIMEOUT="$2"; shift 2 ;;
    --timeout=*)      SUITE_TIMEOUT="${1#--timeout=}"; shift ;;
    --skip-preflight) SKIP_PREFLIGHT=1; shift ;;
    --no-resume)      RESUME=0; shift ;;
    --resume)         RESUME=1; shift ;;
    --force-port)     FORCE_PORT=1; shift ;;
    --stop-on-error)  KEEP_GOING=0; shift ;;
    -n|--dry-run)     DRY_RUN=1; shift ;;
    -l|--list)        DO_LIST=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *) echo "不明なオプション: $1" >&2; usage >&2; exit 1 ;;
  esac
done

# =============================================================================
#  ユーティリティ
# =============================================================================
C_RESET=$'\033[0m'; C_B=$'\033[1m'; C_R=$'\033[31m'; C_G=$'\033[32m'; C_Y=$'\033[33m'
[[ -t 1 ]] || { C_RESET=""; C_B=""; C_R=""; C_G=""; C_Y=""; }

ts()   { date "+%Y-%m-%d %H:%M:%S"; }
log()  { printf '%s [sweep] %s\n' "$(ts)" "$*"; }
info() { printf '%s [sweep] %s%s%s\n' "$(ts)" "$C_B" "$*" "$C_RESET"; }
warn() { printf '%s [sweep] %s%s%s\n' "$(ts)" "$C_Y" "$*" "$C_RESET" >&2; }
err()  { printf '%s [sweep] %s%s%s\n' "$(ts)" "$C_R" "$*" "$C_RESET" >&2; }
die()  { err "$*"; exit 1; }

# 量子化名/スイート名 → 変数名に使える形
varname() { printf '%s' "$1" | tr '.-' '__' | tr '[:lower:]' '[:upper:]'; }
# 間接参照 (未定義でも空文字を返す)
deref()   { local n="$1"; printf '%s' "${!n:-}"; }
# 秒 → h:mm:ss
hms() { local s=$1; printf '%d:%02d:%02d' $((s / 3600)) $((s % 3600 / 60)) $((s % 60)); }

# =============================================================================
#  実行対象の解決
# =============================================================================
list_to_words() { printf '%s' "$1" | tr ',' ' ' | xargs -n1 2>/dev/null || true; }

resolve_quants() {
  local q out=()
  if [[ "${QUANTS,,}" == "auto" ]]; then
    [[ -d "$MODEL_DIR" ]] || die "MODEL_DIR が無い: $MODEL_DIR"
    local f base name
    while IFS= read -r f; do
      base="$(basename "$f")"
      name="${base%.gguf}"
      # 分割 gguf は先頭シャードだけ採用 (-00001-of-0000N)
      if [[ "$name" =~ -[0-9]{5}-of-[0-9]{5}$ ]]; then
        [[ "$name" =~ -00001-of-[0-9]{5}$ ]] || continue
        name="${name%-[0-9][0-9][0-9][0-9][0-9]-of-[0-9][0-9][0-9][0-9][0-9]}"
      fi
      name="${name#"$MODEL_PREFIX"-}"
      if [[ -n "$QUANT_EXCLUDE" ]] && printf '%s' "$name" | grep -Eq "$QUANT_EXCLUDE"; then
        continue
      fi
      out+=("$name")
    done < <(find "$MODEL_DIR" -maxdepth 1 -name '*.gguf' | sort)
  else
    for q in $(list_to_words "$QUANTS"); do out+=("$q"); done
  fi
  printf '%s\n' "${out[@]:-}"
}

# gguf の実ファイルパスを返す (分割は先頭シャード)
gguf_path() {
  local q="$1" p
  p="$MODEL_DIR/${MODEL_PREFIX}-${q}.gguf"
  if [[ -f "$p" ]]; then printf '%s' "$p"; return 0; fi
  p="$MODEL_DIR/${q}.gguf"
  if [[ -f "$p" ]]; then printf '%s' "$p"; return 0; fi
  p="$(find "$MODEL_DIR" -maxdepth 1 -name "*${q}*-00001-of-*.gguf" 2>/dev/null | sort | head -1)"
  if [[ -n "$p" ]]; then printf '%s' "$p"; return 0; fi
  p="$(find "$MODEL_DIR" -maxdepth 1 -name "*${q}*.gguf" 2>/dev/null | sort | head -1)"
  if [[ -n "$p" ]]; then printf '%s' "$p"; return 0; fi
  return 1
}

resolve_suites() {
  local s u want=() sel=""
  [[ -n "$CLI_SUITES" ]] && sel="$(list_to_words "$CLI_SUITES")"
  for s in $(list_to_words "$SUITE_ORDER"); do
    u="$(varname "$s")"
    if [[ -n "$sel" ]]; then
      # --suites 指定時はそこに載っているものだけ
      printf '%s\n' $sel | grep -qx "$s" || continue
    else
      [[ "$(deref "RUN_$u")" == "1" ]] || continue
    fi
    if [[ -n "$CLI_SKIP" ]] && printf '%s\n' $(list_to_words "$CLI_SKIP") | grep -qx "$s"; then
      continue
    fi
    want+=("$s")
  done
  printf '%s\n' "${want[@]:-}"
}

suite_runs() {
  local u; u="$(varname "$1")"
  if [[ -n "$CLI_RUNS" ]]; then printf '%s' "$CLI_RUNS"; return; fi
  printf '%s' "$(deref "RUNS_$u")"
}
suite_args() { local u; u="$(varname "$1")"; printf '%s' "$(deref "ARGS_$u")"; }

# =============================================================================
#  llama-server 制御
# =============================================================================
SERVER_PID=""
SERVER_LOG=""
CURRENT_GGUF=""

# curl は必ず --noproxy を付ける。http_proxy が設定された環境で localhost が
# プロキシに吸われると、いつまでも /health が通らない (実測で踏む)
CURL=(curl -s --noproxy '*')

health_code() {
  local c
  c="$("${CURL[@]}" -o /dev/null -m 5 -w '%{http_code}' "http://$HOST:$PORT/health" 2>/dev/null)" || true
  # 接続失敗時 curl は -w に 000 を出すが、ここで念のため正規化する
  [[ "$c" =~ ^[0-9]{3}$ ]] || c="000"
  printf '%s' "$c"
}

port_busy() { [[ "$(health_code)" != "000" ]]; }

# gguf に MTP (nextn) テンソルがあるか。
#   テンソル名は gguf のヘッダにまとまって置かれているので、先頭だけ読めば分かる。
#   gguf パッケージも python も要らない。分割 gguf は先頭シャードにヘッダがある。
# gguf に MTP テンソルがあるか。
#
#   判定はリポジトリの gguf_probe.py を一次情報にする。テンソル名の付き方は
#   モデルによって nextn / mtp / multi_token と揺れるので、自前のパターンで
#   決め打ちすると取りこぼす (実測で踏んだ)。gguf_probe が使えないときだけ
#   ヘッダを直接 grep する。
#
#   ⚠️ フォールバックの grep を `head | grep -q` にしてはいけない。grep が一致した
#      時点で終了して head が SIGPIPE で死に、pipefail がその 141 を拾って
#      「一致しなかった」ことになる。プロセス置換で grep の終了コードだけを見る。
#   ⚠️ 誤判定の向きは「無い」と言うほうが危険 (黙って MTP を外す = 2倍遅くなる)。
#      付いていて非対応ならサーバが起動に失敗して必ず気づくので、迷ったら広く読む。
MTP_DETECT_BY=""

_gguf_python() {          # gguf パッケージが import できる python を探す
  local p
  for p in "$(dirname "$LLMBENCH")/python3" "$(dirname "$LLMBENCH")/python" python3 python; do
    command -v "$p" >/dev/null 2>&1 || continue
    if "$p" -c 'import gguf' >/dev/null 2>&1; then printf '%s' "$p"; return 0; fi
  done
  return 1
}

gguf_has_mtp() {
  local f="$1" py n
  if [[ "$MTP_DETECT" != "grep" && -f "$REPO_DIR/gguf_probe.py" ]] && py="$(_gguf_python)"; then
    n="$("$py" "$REPO_DIR/gguf_probe.py" "$f" 2>/dev/null \
         | sed -n 's/.*MTP\/nextn[^:]*: *\([0-9][0-9]*\) *本.*/\1/p' | head -1)"
    if [[ -n "$n" ]]; then
      MTP_DETECT_BY="gguf_probe(${n}本)"
      (( n > 0 ))
      return
    fi
  fi
  MTP_DETECT_BY="grep"
  for n in "$MTP_SCAN_BYTES" "$MTP_SCAN_MAX_BYTES"; do
    [[ "$n" =~ ^[0-9]+$ ]] && (( n > 0 )) || continue
    if LC_ALL=C grep -qaE 'blk\.[0-9]+\.(nextn|mtp|multi_token)' \
         < <(head -c "$n" "$f" 2>/dev/null); then
      return 0
    fi
  done
  return 1
}

# SERVER_ARGS から --spec-type draft-mtp (と --spec-type=draft-mtp) を取り除く
strip_mtp_args() {
  local -a out=(); local i n=${#SERVER_ARGS[@]}
  for ((i = 0; i < n; i++)); do
    if [[ "${SERVER_ARGS[$i]}" == "--spec-type" && "${SERVER_ARGS[$((i + 1))]:-}" == "draft-mtp" ]]; then
      i=$((i + 1)); continue
    fi
    [[ "${SERVER_ARGS[$i]}" == "--spec-type=draft-mtp" ]] && continue
    out+=("${SERVER_ARGS[$i]}")
  done
  SERVER_ARGS=("${out[@]}")
}

MTP_USED="-"
build_server_args() {
  local q="$1" gguf="$2" ov
  SERVER_ARGS=(-m "$gguf" --host "$HOST" --port "$PORT"
               -ngl "$NGL" --ctx-size "$CTX" --parallel "$PARALLEL"
               --batch-size "$BATCH" --ubatch-size "$UBATCH")
  [[ -n "$FLASH_ATTN"   ]] && SERVER_ARGS+=(-fa "$FLASH_ATTN")
  [[ -n "$KV_TYPE"      ]] && SERVER_ARGS+=(-ctk "$KV_TYPE" -ctv "$KV_TYPE")
  [[ -n "$DEVICE"       ]] && SERVER_ARGS+=(--device "$DEVICE")
  [[ -n "$TENSOR_SPLIT" ]] && SERVER_ARGS+=(--tensor-split "$TENSOR_SPLIT")
  # shellcheck disable=SC2206
  [[ -n "$SERVER_EXTRA_ARGS" ]] && SERVER_ARGS+=($SERVER_EXTRA_ARGS)
  ov="$(deref "OVERRIDE_$(varname "$q")")"
  # shellcheck disable=SC2206
  [[ -n "$ov" ]] && SERVER_ARGS+=($ov)

  # --- MTP (投機デコード) の自動判定 -------------------------------------
  MTP_USED="-"
  local a requested=0
  for a in "${SERVER_ARGS[@]}"; do
    [[ "$a" == "draft-mtp" || "$a" == "--spec-type=draft-mtp" ]] && requested=1
  done
  if (( requested )); then
    if [[ "$MTP_AUTO" == "1" ]] && ! gguf_has_mtp "$gguf"; then
      warn "  ⚠️ この gguf に MTP テンソルがないため --spec-type draft-mtp を外します [判定: ${MTP_DETECT_BY:-?}]"
      warn "     (付けたままだと llama-server は起動に失敗します)"
      warn "     速度は MTP 有りの量子化と比較できません。manifest の mtp 列を確認すること"
      strip_mtp_args
      MTP_USED="no"
    else
      MTP_USED="yes"
      log "  MTP 判定: ${MTP_DETECT_BY:-?}"
    fi
  fi
  return 0
}

start_server() {
  local q="$1" gguf="$2"
  SERVER_LOG="$LOG_DIR/${q}_server.log"
  build_server_args "$q" "$gguf"

  if [[ "$DRY_RUN" == "1" ]]; then
    [[ "$MTP_USED" != "-" ]] && log "  MTP: $MTP_USED"
    log "DRY-RUN: $LLAMA_SERVER ${SERVER_ARGS[*]}  > $SERVER_LOG"
    return 0
  fi

  if port_busy; then
    if [[ "$FORCE_PORT" == "1" ]]; then
      warn "ポート $PORT に既存プロセス。落とす (--force-port)"
      pkill -f -- "--port $PORT" || true
      sleep 3
      port_busy && die "ポート $PORT を解放できなかった"
    else
      die "ポート $PORT は既に使用中。--force-port を付けるか手動で停止すること"
    fi
  fi

  info "llama-server 起動: $q"
  [[ "$MTP_USED" != "-" ]] && log "  MTP: $MTP_USED"
  log  "  $LLAMA_SERVER ${SERVER_ARGS[*]}"
  "$LLAMA_SERVER" "${SERVER_ARGS[@]}" >"$SERVER_LOG" 2>&1 &
  SERVER_PID=$!

  local waited=0 code
  while (( waited < HEALTH_TIMEOUT )); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      err "llama-server が起動直後に落ちた。ログ末尾:"
      tail -n 20 "$SERVER_LOG" >&2 || true
      SERVER_PID=""
      return 1
    fi
    code="$(health_code)"
    if [[ "$code" == "200" ]]; then
      log "  /health OK (${waited}s)"
      return 0
    fi
    sleep 3; waited=$((waited + 3))
    (( waited % 60 == 0 )) && log "  ロード待ち ${waited}s (HTTP $code)"
  done
  err "/health が ${HEALTH_TIMEOUT}s 以内に通らなかった"
  return 1
}

stop_server() {
  [[ "$DRY_RUN" == "1" ]] && { SERVER_PID=""; return 0; }
  [[ -n "$SERVER_PID" ]] || return 0
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    log "llama-server 停止 (pid $SERVER_PID)"
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    local waited=0
    while (( waited < STOP_WAIT )) && kill -0 "$SERVER_PID" 2>/dev/null; do
      sleep 1; waited=$((waited + 1))
    done
    if kill -0 "$SERVER_PID" 2>/dev/null; then
      warn "SIGTERM で落ちないので SIGKILL"
      kill -9 "$SERVER_PID" 2>/dev/null || true
    fi
  fi
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
  (( VRAM_SETTLE > 0 )) && sleep "$VRAM_SETTLE"
  return 0
}

record_server_env() {
  local q="$1"
  [[ "$DRY_RUN" == "1" ]] && return 0
  "${CURL[@]}" -m 10 "http://$HOST:$PORT/props"     -o "$LOG_DIR/${q}_props.json"  || true
  "${CURL[@]}" -m 10 "http://$HOST:$PORT/v1/models" -o "$LOG_DIR/${q}_models.json" || true
  local loaded n_ctx
  loaded="$(python3 - "$LOG_DIR/${q}_models.json" <<'PY' 2>/dev/null || true
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print((d.get("data") or [{}])[0].get("id",""))
except Exception:
    print("")
PY
)"
  n_ctx="$(python3 - "$LOG_DIR/${q}_props.json" <<'PY' 2>/dev/null || true
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    g=d.get("default_generation_settings") or {}
    print(g.get("n_ctx") or d.get("n_ctx") or "")
except Exception:
    print("")
PY
)"
  log "  ロード中モデル: ${loaded:-?}  / n_ctx: ${n_ctx:-?}"

  # --- GPU に本当に載ったかを確認する -------------------------------------
  #   -ngl 99 を付けていても、VRAM が足りなければ llama.cpp は一部の層を
  #   CPU に置く。生成が数十倍遅くなるが、ログには何も出ない (実測で踏む)。
  #   モデルファイルの半分も VRAM を使っていなければ警告する。
  #   GPU は1枚とは限らないので、全 GPU を合計して見る (tensor-split 対応)。
  local gpu_used=0 gpu_total=0 gpu_lines=""
  if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_lines="$(nvidia-smi --query-gpu=index,name,memory.used,memory.total \
                 --format=csv,noheader,nounits 2>/dev/null || true)"
    if [[ -n "$gpu_lines" ]]; then
      local idx name used total
      while IFS=, read -r idx name used total; do
        used="$(printf '%s' "$used" | tr -d ' ')"
        total="$(printf '%s' "$total" | tr -d ' ')"
        [[ "$used"  =~ ^[0-9]+$ ]] || continue
        [[ "$total" =~ ^[0-9]+$ ]] || total=0
        log "  VRAM GPU${idx// /}:$(printf '%s' "$name") ${used}/${total} MiB"
        gpu_used=$((gpu_used + used)); gpu_total=$((gpu_total + total))
      done <<< "$gpu_lines"
      # du はディスク使用量なので使わない (スパースだと 0 になる)。実サイズを見る。
      local file_bytes file_mib
      file_bytes="$(stat -c %s "$CURRENT_GGUF" 2>/dev/null || stat -f %z "$CURRENT_GGUF" 2>/dev/null || echo 0)"
      file_mib=$(( file_bytes / 1048576 ))
      if (( gpu_used > 0 )); then
        log "  VRAM 合計: ${gpu_used}/${gpu_total} MiB"
      fi
      if [[ -n "$file_mib" ]] && (( gpu_used * 2 < file_mib )); then
        warn "  ⚠️ VRAM 使用量 (合計 ${gpu_used} MiB) がモデルサイズ (${file_mib} MiB) の半分未満。"
        warn "     GPU に載り切っていない (= CPU 実行で極端に遅い) 可能性が高い。"
        warn "     DEVICE / TENSOR_SPLIT の指定、--ctx-size を下げる、KV_TYPE=q8_0 を検討すること。"
        warn "     ログ: $SERVER_LOG"
      fi
    fi
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$q" "${loaded:-?}" "${n_ctx:-?}" \
         "${gpu_used:-?}" "${gpu_total:-?}" "${MTP_USED:--}" >> "$OUT_ROOT/manifest_${RUN_ID}.tsv"
}

# =============================================================================
#  config (seed 無効化)
# =============================================================================
# 量子化ごとの実効 ctx (共通 CTX を SERVER_EXTRA_ARGS / OVERRIDE_* が後勝ちで上書き)
effective_ctx() {
  local q="$1" ctx="$CTX" tok prev="" s
  s="$SERVER_EXTRA_ARGS $(deref "OVERRIDE_$(varname "$q")")"
  for tok in $s; do
    case "$prev" in
      --ctx-size|-c) [[ "$tok" =~ ^[0-9]+$ ]] && ctx="$tok" ;;
    esac
    prev="$tok"
  done
  printf '%s' "$ctx"
}

# config に書かれている max_tokens (MODEL_KEY のブロック内) を読む
config_max_tokens() {
  awk -v key="$MODEL_KEY" '
    /^[^[:space:]#]/                { inblk = 0 }
    $0 ~ "^  " key ":[[:space:]]*$" { inblk = 1; next }
    inblk && /^  [A-Za-z0-9_.\-]+:[[:space:]]*$/ { inblk = 0 }
    inblk && match($0, /^[[:space:]]*max_tokens:[[:space:]]*[0-9]+/) {
      s = substr($0, RSTART, RLENGTH); gsub(/[^0-9]/, "", s); print s; exit
    }
  ' "$CONFIG"
}

# 実効 ctx に対して安全な max_tokens。gguf_plan.py と同じ規則:
#   min(ctx の 3/4 を 1024 単位に切り下げ, MAX_TOKENS_CAP)
auto_max_tokens() {
  local ctx="$1" tq=$(( $1 * 3 / 4 / 1024 * 1024 ))
  if (( tq <= MAX_TOKENS_CAP )); then printf '%s' "$tq"; else printf '%s' "$MAX_TOKENS_CAP"; fi
}

# 量子化 × (seed を落とすか) ごとに一時 config を作る。元の config.yaml は読むだけ。
CONFIG_NOTE=""
CONFIG_PATH=""
config_for() {   # 結果は CONFIG_PATH / CONFIG_NOTE に入れる (サブシェルにしない)
  local q="$1" runs="$2"
  local strip=0 ctx mt cur out tag
  CONFIG_NOTE=""
  [[ -f "$CONFIG" ]] || die "config が無い: $CONFIG"

  if [[ "$STRIP_SEED_FOR_MULTIRUN" == "1" && "${runs:-1}" -gt 1 ]]; then strip=1; fi

  mt=""
  if [[ "$ADJUST_MAX_TOKENS" == "1" ]]; then
    ctx="$(effective_ctx "$q")"
    if [[ -n "$MAX_TOKENS" ]]; then mt="$MAX_TOKENS"; else mt="$(auto_max_tokens "$ctx")"; fi
    cur="$(config_max_tokens)"
    # 元の値より小さくするときだけ書き換える (ctx を上げても勝手に増やさない)
    if [[ -n "$cur" ]] && (( cur <= mt )); then mt=""; fi
  fi

  if (( strip == 0 )) && [[ -z "$mt" ]]; then
    CONFIG_PATH="$CONFIG"; return 0
  fi

  tag="$(varname "$q")"; (( strip )) && tag="${tag}_noseed"
  out="$OUT_ROOT/config_${tag}.yaml"
  awk -v key="$MODEL_KEY" -v strip="$strip" -v mt="$mt" '
    /^[^[:space:]#]/                { inblk = 0 }
    $0 ~ "^  " key ":[[:space:]]*$" { inblk = 1; print; next }
    inblk && /^  [A-Za-z0-9_.\-]+:[[:space:]]*$/ { inblk = 0 }
    inblk && strip == 1 && /^[[:space:]]*seed:/ {
      print "#" $0 "   # sweep.sh: runs>1 のため無効化"; next
    }
    inblk && mt != "" && match($0, /^[[:space:]]*max_tokens:[[:space:]]*[0-9]+/) {
      indent = $0; sub(/[^[:space:]].*$/, "", indent)
      print indent "max_tokens: " mt "   # sweep.sh: 実効 ctx に合わせて引き下げ"
      next
    }
    { print }
  ' "$CONFIG" > "$out"

  if (( strip )); then CONFIG_NOTE="seed 無効化"; fi
  if [[ -n "$mt" ]]; then
    CONFIG_NOTE="${CONFIG_NOTE:+$CONFIG_NOTE / }max_tokens ${cur:-?} → $mt (ctx $ctx)"
  fi
  CONFIG_PATH="$out"
}

# =============================================================================
#  state (resume)
# =============================================================================
STATE_FILE=""
state_key()  { printf '%s\t%s' "$1" "$2"; }
state_done() {
  [[ "$RESUME" == "1" ]] || return 1
  [[ -f "$STATE_FILE" ]] || return 1
  awk -F'\t' -v q="$1" -v s="$2" '$1==q && $2==s && $3=="ok" {found=1} END{exit !found}' "$STATE_FILE"
}
state_put() {  # quant suite status seconds results_path
  [[ "$DRY_RUN" == "1" ]] && return 0    # DRY-RUN は state を汚さない
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "${5:-}" >> "$STATE_FILE"
}
summary_put() {  # quant suite status seconds results_path
  [[ "$DRY_RUN" == "1" ]] && return 0
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "${5:-}" >> "$SUMMARY"
}

# =============================================================================
#  1スイート実行
# =============================================================================
run_suite() {  # quant suite -> 0/1, RESULT_PATH に結果 json
  local q="$1" s="$2"
  local runs args label logf cfg rc started elapsed
  runs="$(suite_runs "$s")"; args="$(suite_args "$s")"
  label="${LABEL_PREFIX:+${LABEL_PREFIX}-}${q}-${s}"
  logf="$LOG_DIR/${q}_${s}.log"
  RESULT_PATH=""

  config_for "$q" "$runs"
  cfg="$CONFIG_PATH"
  if [[ "$cfg" != "$CONFIG" ]]; then
    log "  config: $(basename "$cfg")  [${CONFIG_NOTE:-一時config}]"
  fi

  # llmbench の進捗 (print) は stdout。tee にパイプすると Python が
  # ブロックバッファリングに切り替わり、数KB 貯まるまで1行も出ない
  # (実測: L6 の1タスク目を生成している間ずっと画面が止まって見える)。
  # PYTHONUNBUFFERED=1 で行ごとに流す。stdbuf があれば併用する。
  local -a unbuf=(env PYTHONUNBUFFERED=1)
  if command -v stdbuf >/dev/null 2>&1; then unbuf+=(stdbuf -oL -eL); fi

  local cmd=("${unbuf[@]}" "$LLMBENCH" run --model "$MODEL_KEY" --config "$cfg"
             --tasks-dir "$TASKS_DIR" --output "$RESULTS_DIR"
             --label "$label" --runs "$runs")
  # shellcheck disable=SC2206
  cmd+=($args)
  [[ -n "$CONCURRENCY" ]] && cmd+=(--concurrency "$CONCURRENCY")
  [[ "$SKIP_PREFLIGHT" == "1" ]] && cmd+=(--skip-preflight)
  if (( SUITE_TIMEOUT > 0 )) && command -v timeout >/dev/null 2>&1; then
    cmd=(timeout "${SUITE_TIMEOUT}s" "${cmd[@]}")
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: (cd $REPO_DIR && ${cmd[*]})"
    return 0
  fi

  info "  ▶ $q / $s  (runs=$runs $args)"
  started=$SECONDS
  set +e
  ( cd "$REPO_DIR" && "${cmd[@]}" ) 2>&1 | tee "$logf"
  rc=${PIPESTATUS[0]}
  set -e
  elapsed=$((SECONDS - started))

  RESULT_PATH="$(grep -a '^結果: ' "$logf" | tail -1 | sed 's/^結果: //' || true)"
  if [[ -z "$RESULT_PATH" ]]; then
    RESULT_PATH="$(find "$RESULTS_DIR" -maxdepth 1 -name "*_${label}_results.json" 2>/dev/null | sort | tail -1)"
  fi

  if [[ $rc -eq 0 ]]; then
    log "  ✅ $q / $s  $(hms "$elapsed")  ${RESULT_PATH:-(結果パス不明)}"
  else
    err "  ❌ $q / $s  rc=$rc  $(hms "$elapsed")  ログ: $logf"
    if [[ $rc -eq 2 ]] && grep -qa "preflight が FAIL" "$logf" 2>/dev/null; then
      err "     preflight が FAIL。ログの「B. 実効値の三点照合」を見て config か"
      err "     起動引数を直すこと (承知の上で走らせるなら SKIP_PREFLIGHT=1)"
    fi
  fi
  SUITE_ELAPSED=$elapsed
  return $rc
}

# =============================================================================
#  main
# =============================================================================
RUN_ID="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$OUT_ROOT/logs/$RUN_ID"
STATE_FILE="$OUT_ROOT/sweep_state${LABEL_PREFIX:+_${LABEL_PREFIX}}.tsv"
SUMMARY="$OUT_ROOT/summary_${RUN_ID}.tsv"

mapfile -t QUANT_LIST < <(resolve_quants)
mapfile -t SUITE_LIST < <(resolve_suites)
QUANT_LIST=("${QUANT_LIST[@]:-}"); SUITE_LIST=("${SUITE_LIST[@]:-}")
[[ -n "${QUANT_LIST[0]:-}" ]] || die "対象の量子化が0件 (QUANTS=$QUANTS)"
[[ -n "${SUITE_LIST[0]:-}" ]] || die "対象のスイートが0件 (RUN_* が全部0か --suites が空)"

if [[ "$DO_LIST" == "1" ]]; then
  echo "設定ファイル: ${SWEEP_CONF_LOADED:-(読み込みなし — スクリプト既定値)}"
  echo "REPO_DIR  : $REPO_DIR"
  echo "LLMBENCH  : $LLMBENCH"
  echo "CONFIG    : $CONFIG"
  echo "OUT_ROOT  : $OUT_ROOT"
  echo "RESULTS   : $RESULTS_DIR"
  echo "MODEL_DIR : $MODEL_DIR"
  echo "MODEL_PFX : $MODEL_PREFIX"
  echo "LABEL_PFX : ${LABEL_PREFIX:-(なし)}"
  echo "量子化    : ${QUANT_LIST[*]}"
  echo "スイート  :"
  for s in "${SUITE_LIST[@]}"; do
    printf '  %-8s runs=%-3s %s\n' "$s" "$(suite_runs "$s")" "$(suite_args "$s")"
  done
  echo "合計      : $(( ${#QUANT_LIST[@]} * ${#SUITE_LIST[@]} )) 実行"
  exit 0
fi

mkdir -p "$LOG_DIR" "$RESULTS_DIR"
touch "$STATE_FILE"

# 二重起動防止
LOCK_FILE="$OUT_ROOT/.sweep.lock"
if [[ "$DRY_RUN" != "1" ]]; then
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    flock -n 9 || die "他の sweep が実行中 ($LOCK_FILE)"
    echo "$$" >&9
  fi
fi

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  [[ -n "$SERVER_PID" ]] && { warn "後片付け: llama-server を停止"; stop_server; }
  exit $rc
}
trap cleanup EXIT INT TERM

info "════════ llmbench sweep $RUN_ID ════════"
log "設定     : ${SWEEP_CONF_LOADED:-(読み込みなし — スクリプト既定値)}"
log "量子化   : ${QUANT_LIST[*]}"
log "スイート : ${SUITE_LIST[*]}"
log "ログ     : $LOG_DIR"
[[ "$DRY_RUN" == "1" ]] && warn "DRY-RUN モード (実行しない)"

mkdir -p "$OUT_ROOT"
if [[ "$DRY_RUN" != "1" ]]; then
  printf 'quant\tmodel_id\tn_ctx\tvram_used_mib\tvram_total_mib\tmtp\n' > "$OUT_ROOT/manifest_${RUN_ID}.tsv"
  printf 'quant\tsuite\tstatus\tseconds\tresults\n' > "$SUMMARY"
fi

TOTAL=0; OK=0; NG=0; SKIP=0
SWEEP_START=$SECONDS

for q in "${QUANT_LIST[@]}"; do
  echo
  info "──────── 量子化: $q ────────"

  # このモデルで走らせるものが残っているか (resume)
  pending=()
  for s in "${SUITE_LIST[@]}"; do
    if state_done "$q" "$s"; then
      log "  ⏭ $q / $s は完了済み → スキップ"
      SKIP=$((SKIP + 1)); TOTAL=$((TOTAL + 1))
      summary_put "$q" "$s" "skipped" 0 ""
    else
      pending+=("$s")
    fi
  done
  if [[ ${#pending[@]} -eq 0 ]]; then
    log "  この量子化は全て完了済み。サーバは起動しない"
    continue
  fi

  gguf="$(gguf_path "$q" || true)"
  if [[ -z "$gguf" ]]; then
    err "  gguf が見つからない: ${MODEL_PREFIX}-${q}.gguf ($MODEL_DIR)"
    for s in "${pending[@]}"; do
      TOTAL=$((TOTAL + 1)); NG=$((NG + 1))
      state_put "$q" "$s" "no_model" 0 ""
      summary_put "$q" "$s" "no_model" 0 ""
    done
    [[ "$KEEP_GOING" == "1" ]] && continue || exit 1
  fi
  CURRENT_GGUF="$gguf"
  log "  gguf: $gguf ($(du -h "$gguf" 2>/dev/null | cut -f1))"

  if ! start_server "$q" "$gguf"; then
    err "  サーバ起動失敗 → この量子化をスキップ"
    stop_server
    for s in "${pending[@]}"; do
      TOTAL=$((TOTAL + 1)); NG=$((NG + 1))
      state_put "$q" "$s" "server_fail" 0 ""
      summary_put "$q" "$s" "server_fail" 0 ""
    done
    [[ "$KEEP_GOING" == "1" ]] && continue || exit 1
  fi
  record_server_env "$q"

  for s in "${pending[@]}"; do
    TOTAL=$((TOTAL + 1))
    SUITE_ELAPSED=0
    if run_suite "$q" "$s"; then
      OK=$((OK + 1))
      state_put "$q" "$s" "ok" "$SUITE_ELAPSED" "$RESULT_PATH"
      summary_put "$q" "$s" "ok" "$SUITE_ELAPSED" "$RESULT_PATH"
    else
      NG=$((NG + 1))
      state_put "$q" "$s" "failed" "$SUITE_ELAPSED" ""
      summary_put "$q" "$s" "failed" "$SUITE_ELAPSED" ""
      if [[ "$KEEP_GOING" != "1" ]]; then
        stop_server
        die "スイート失敗により打ち切り (--stop-on-error)"
      fi
    fi
  done

  stop_server
done

# --- サマリ -----------------------------------------------------------------
echo
info "════════ サマリ ($(hms $((SECONDS - SWEEP_START)))) ════════"
if [[ "$DRY_RUN" != "1" ]]; then
  {
    printf '%-14s %-9s %-11s %-9s %s\n' "QUANT" "SUITE" "STATUS" "TIME" "RESULTS"
    tail -n +2 "$SUMMARY" | while IFS=$'\t' read -r q s st sec res; do
      printf '%-14s %-9s %-11s %-9s %s\n' "$q" "$s" "$st" "$(hms "${sec:-0}")" "${res:-}"
    done
  } | sed 's/^/  /'
  echo
  log "合計 $TOTAL  /  成功 $OK  /  失敗 $NG  /  スキップ $SKIP"
  log "サマリ  : $SUMMARY"
  log "manifest: $OUT_ROOT/manifest_${RUN_ID}.tsv"
  log "state   : $STATE_FILE  (--resume で完了済みを飛ばす)"
  echo
  log "スイート横断の比較レポートは次で作れる:"
  for s in "${SUITE_LIST[@]}"; do
    files="$(awk -F'\t' -v s="$s" '$3=="ok" && $2==s {print $5}' "$SUMMARY" | tr '\n' ' ')"
    [[ -n "${files// /}" ]] && echo "  $LLMBENCH compare $files --name ${s}_by_quant"
  done
fi

[[ $NG -gt 0 ]] && exit 1
exit 0
