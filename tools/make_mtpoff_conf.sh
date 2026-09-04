#!/usr/bin/env bash
# =============================================================================
#  make_mtpoff_conf.sh
#
#  「MTP テンソル入りの同一 gguf を、投機デコードだけ切って回す」ための conf を
#  作る。既存の _OUTPUTS/sweep_dual/20260903_make_variant_confs_v1.sh が作る 2本
#
#      tools/sweep_mtp.conf    MODEL_PREFIX=<..>-MTP  LABEL_PREFIX=mtp
#      tools/sweep_nomtp.conf  MODEL_PREFIX=<..>      LABEL_PREFIX=nomtp
#
#  は **モデルファイル自体が違う** ので、投機デコード起因かどうかを切り分け
#  られない (重み差と復号経路差が交絡する)。本スクリプトが作る
#
#      tools/sweep_mtpoff.conf MODEL_PREFIX=<..>-MTP  LABEL_PREFIX=mtpoff
#                              SERVER_EXTRA_ARGS=""   (= --spec-type を渡さない)
#
#  は mtp 版と **同一 gguf・同一パラメータ** で復号経路だけが違う。
#  mtp と mtpoff の差分 = 投機デコードの寄与、と一意に読める。
#
#  使い方:  bash tools/make_mtpoff_conf.sh
# =============================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SRC="$REPO_DIR/tools/sweep.conf"
DST="$REPO_DIR/tools/sweep_mtpoff.conf"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f "$SRC" ]] || die "tools/sweep.conf が無い: $SRC"
grep -q '^LABEL_PREFIX=' "$REPO_DIR/tools/sweep.sh" \
  || die "tools/sweep.sh が LABEL_PREFIX 未対応。feature/sweep-label-prefix を取り込むこと"

eval "$(bash -c 'set +u; source "$1" >/dev/null 2>&1
  printf "MP=%q\n" "$MODEL_PREFIX"' _ "$SRC")"
[[ -n "${MP:-}" ]] || die "sweep.conf に MODEL_PREFIX が無い"
MTP="${MP%-MTP}-MTP"

{
  cat "$SRC"
  cat <<VAREOF

# ── バリアント指定 (tools/make_mtpoff_conf.sh が生成) ──
#  MTP テンソル入りの gguf を、投機デコードだけ切って回す条件。
#  SERVER_EXTRA_ARGS を **空で明示上書き** する (上流でセットされていても無効化)。
MODEL_PREFIX=$MTP
LABEL_PREFIX=mtpoff
SERVER_EXTRA_ARGS=""
#  切り分けを速くするため Q4_K_M だけ・1周だけ回す。差が出たら runs=5 で再計測する。
QUANTS="Q4_K_M"
RUNS_L6=1
VAREOF
} > "$DST"

echo "✅ 生成: $DST  (MODEL_PREFIX=$MTP / LABEL_PREFIX=mtpoff / SERVER_EXTRA_ARGS='')"
cat <<MSG

確認:
  ./tools/sweep.sh -c tools/sweep_mtpoff.conf --list
  ./tools/sweep.sh -c tools/sweep_mtpoff.conf --dry-run     # ← --spec-type が消えているか目視

本番 (条件A):
  ./tools/sweep.sh -c tools/sweep_mtpoff.conf

判定:
  python3 tools/check_indent_collapse.py \\
      results/*_mtpoff-Q4_K_M-l6_artifacts
  → COLLAPSED=0 なら投機デコード起因で確定。
MSG
