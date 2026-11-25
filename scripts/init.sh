#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet --disable-pip-version-check --requirement requirements.txt
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example - set SECRET_KEY and JWT_SECRET." >&2
fi
