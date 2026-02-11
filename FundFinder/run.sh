#!/usr/bin/env bash
# Run show_grants.py using the project venv (creates venv + installs deps if needed).
set -e
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
if ! .venv/bin/python3 -c "import pydantic" 2>/dev/null; then
  echo "Installing dependencies..."
  .venv/bin/pip install -q -r requirements.txt
fi

.venv/bin/python3 scripts/show_grants.py
