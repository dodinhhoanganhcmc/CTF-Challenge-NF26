#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
TARGET="${1:?Usage: ROLLBACK.sh ABSOLUTE_PROJECT_OR_DEDICATED_ROLLBACK_COPY}"
PYTHON="${PYTHON:-$HERE/../../.venv/Scripts/python.exe}"
exec "$PYTHON" "$HERE/rollback.py" "$TARGET"
