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
  p="$(find "$MODEL_DIR" -maxdepth 1 -name "*${q}*-00001-of-*.gguf" | sort | head -1)"
  if [[ -n "$p" ]]; then printf '%s' "$p"; return 0; fi
  p="$(find "$MODEL_DIR" -maxdepth 1 -name "*${q}*.gguf" | sort | head -1)"
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
  return 0
}

start_server() {
  local q="$1" gguf="$2"
  SERVER_LOG="$LOG_DIR/${q}_server.log"
  build_server_args "$q" "$gguf"

  if [[ "$DRY_RUN" == "1" ]]; then
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
  printf '%s\t%s\t%s\n' "$q" "${loaded:-?}" "${n_ctx:-?}" >> "$OUT_ROOT/manifest_${RUN_ID}.tsv"
}

# =============================================================================
#  config (seed 無効化)
# =============================================================================
CONFIG_MULTIRUN="$CONFIG"

prepare_config() {
  [[ "$STRIP_SEED_FOR_MULTIRUN" == "1" ]] || return 0
  [[ -f "$CONFIG" ]] || die "config が無い: $CONFIG"
  local out="$OUT_ROOT/config_noseed.yaml"
  awk -v key="$MODEL_KEY" '
    BEGIN { inblk = 0; hit = 0 }
    /^[^[:space:]#]/           { inblk = 0 }
    $0 ~ "^  " key ":[[:space:]]*$" { inblk = 1; print; next }
    inblk && /^  [A-Za-z0-9_.\-]+:[[:space:]]*$/ { inblk = 0 }
    inblk && /^[[:space:]]*seed:/ {
      print "#" $0 "   # sweep.sh: runs>1 のため無効化"
      hit = 1; next
    }
    { print }
  ' "$CONFIG" > "$out"
  if diff -q "$CONFIG" "$out" >/dev/null 2>&1; then
    log "config: $MODEL_KEY に seed 指定なし → そのまま使う"
    CONFIG_MULTIRUN="$CONFIG"
    rm -f "$out"
  else
    warn "config: $MODEL_KEY の seed を無効化した一時 config を使う (runs>1 のスイートのみ)"
    log  "  $out"
    CONFIG_MULTIRUN="$out"
  fi
  return 0
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
  label="${q}-${s}"
  logf="$LOG_DIR/${q}_${s}.log"
  RESULT_PATH=""

  cfg="$CONFIG"
  if [[ "$STRIP_SEED_FOR_MULTIRUN" == "1" && "${runs:-1}" -gt 1 ]]; then
    cfg="$CONFIG_MULTIRUN"
  fi

  local cmd=("$LLMBENCH" run --model "$MODEL_KEY" --config "$cfg"
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
  fi
  SUITE_ELAPSED=$elapsed
  return $rc
}

# =============================================================================
#  main
# =============================================================================
RUN_ID="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$OUT_ROOT/logs/$RUN_ID"
STATE_FILE="$OUT_ROOT/sweep_state.tsv"
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

prepare_config
if [[ "$DRY_RUN" != "1" ]]; then
  printf 'quant\tmodel_id\tn_ctx\n' > "$OUT_ROOT/manifest_${RUN_ID}.tsv"
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
