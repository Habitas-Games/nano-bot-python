#!/usr/bin/env bash
# Launches nano-bot. Sets up the virtualenv on first run if it doesn't
# exist yet, then starts the pygame app. Run from anywhere:
#   ./run.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment (first run only)..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
fi

exec .venv/bin/python main.py "$@"
