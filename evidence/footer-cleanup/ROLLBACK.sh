#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
TARGET="${1:?Usage: ROLLBACK.sh ABSOLUTE_PROJECT_OR_DEDICATED_ROLLBACK_COPY}"
PYTHON="${PYTHON:-$HERE/../../.venv/Scripts/python.exe}"
"$PYTHON" "$HERE/rollback.py" "$TARGET"
cd -- "$TARGET"
npm ci --no-audit --no-fund
npm run build
echo ROLLBACK_BUILD_OK
