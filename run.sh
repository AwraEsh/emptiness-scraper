#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Python 3.11 or newer is required. Install Python and run this file again."
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Python 3.11 or newer is required. Your current interpreter is too old."
    exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
    echo "Creating the private Python environment..."
    "$PYTHON_BIN" -m venv .venv
fi

export PYTHONUTF8=1
echo "Checking required packages..."
.venv/bin/python -m pip install --disable-pip-version-check --quiet -r requirements.txt
exec .venv/bin/python -m emptiness_scraper

