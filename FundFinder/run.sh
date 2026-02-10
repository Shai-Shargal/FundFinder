#!/usr/bin/env bash
# Run show_grants.py using the project venv (no need to activate first).
cd "$(dirname "$0")"
.venv/bin/python3 scripts/show_grants.py
