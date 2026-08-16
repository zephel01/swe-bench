#!/usr/bin/env bash
# テスト実行。リポジトリ同梱の .venv が壊れているため uv で隔離実行する。
#
#   ./run_tests.sh              # 全テスト
#   ./run_tests.sh -k preflight # 絞り込み (pytest の引数はそのまま渡る)
#
# uv が無い環境では、依存を入れた python で直接:
#   python -m pytest tests -q
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null 2>&1; then
  exec uv run --python 3.12 \
      --with pytest --with pytest-asyncio --with ruff --with radon \
      --with pyyaml --with requests \
      python -m pytest tests -q "$@"
fi

echo "uv が見つかりません。現在の python で実行します" >&2
exec python -m pytest tests -q "$@"
