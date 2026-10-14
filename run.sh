#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$PROJECT_DIR/run.py"
elif command -v python >/dev/null 2>&1; then
    exec python "$PROJECT_DIR/run.py"
else
    echo "Install Python 3.11 or newer, then run this launcher again."
    exit 1
fi

