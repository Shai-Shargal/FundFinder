"""Run scrapers and print grant results.

Run from project root (FundFinder/) using the venv:
  ./run.sh
  or:  .venv/bin/python3 scripts/show_grants.py
Do not use /usr/bin/python3 (no project deps).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Fix Windows console Unicode (cp1252 can't encode Hebrew)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from services.scraper.pipeline import get_all_scrapers, run_sources

grants = run_sources(get_all_scrapers())
print(f"Found {len(grants)} grant(s)\n")
for i, g in enumerate(grants, 1):
    print(f"--- Grant {i} ---")
    print(f"  title:       {(g.title)}")
    print(f"  description: {(g.description)}")
    print(f"  source_url:  {g.source_url}")
    print(f"  deadline:    {g.deadline}")
    print(f"  deadline_text: {g.deadline_text}")
    print(f"  amount:      {g.amount}")
    print(f"  content_hash: {g.content_hash}")
    print()
