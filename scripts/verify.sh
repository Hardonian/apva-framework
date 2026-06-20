#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
LOG_DIR="${LOG_DIR:-/tmp/apva-framework-verify}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/verify-$(date +%Y%m%d_%H%M%S).log"
exec > >(tee "$LOG") 2>&1

echo "=== APVA framework verify ==="
echo "repo=$(pwd)"
python_bin="${PYTHON:-.venv/bin/python}"

rm -f .apva-test.db

echo "--- syntax ---"
"$python_bin" -m py_compile \
  apva/*.py \
  packages/cli/src/apva_cli/*.py \
  packages/sdk/src/apva_sdk/*.py \
  apps/backend/apps/backend/*.py \
  apps/backend/apps/backend/routers/*.py \
  apps/backend/apps/backend/services/*.py \
  tests/conftest.py

echo "--- tests ---"
"$python_bin" -m pytest -q

echo "--- CLI smoke ---"
"$python_bin" -m apva.cli demo | python3 -m json.tool >/tmp/apva-demo.json
if [ -x .venv/bin/apva ]; then
  .venv/bin/apva run-eval --golden-set data/golden_dataset.json | python3 -m json.tool >/tmp/apva-cli-eval.json
else
  "$python_bin" -m apva_cli.main run-eval --golden-set data/golden_dataset.json | python3 -m json.tool >/tmp/apva-cli-eval.json
fi

echo "APVA demo/eval smoke ok"
echo "VERIFY_LOG=$LOG"
