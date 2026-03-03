"""Run the Miluim student grant (Playwright) scraper and print the grant(s) found.

Run from FundFinder project root with the project env activated, e.g.:
  cd FundFinder
  source .venv/bin/activate
  python scripts/run_miluim_student_grant.py

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so "services" resolves when run as script
_root = Path(__file__).resolve().parent.parent
if _root not in sys.path:
    sys.path.insert(0, str(_root))

from services.scraper.sources.government.miluim_student_grant import MiluimStudentGrantSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    scraper = MiluimStudentGrantSource()
    print("Running Miluim student grant scraper (Playwright)...")
    print()

    grants = scraper.scrape()
    total = len(grants)

    print(f"Total grants found: {total}")
    print("=" * 60)

    for i, g in enumerate(grants, 1):
        print(f"\n--- Grant {i} ---")
        print(f"  Title:       {g.title}")
        print(f"  Source URL:  {g.source_url}")
        print(f"  Deadline:    {g.deadline}  (raw: {g.deadline_text or '-'})")
        print(f"  Amount:      {g.amount or '-'}  {g.currency or ''}")
        if g.eligibility:
            elig = g.eligibility.strip()
            if len(elig) > 300:
                elig = elig[:300] + "..."
            print(f"  Eligibility: {elig}")
        else:
            print("  Eligibility: (none)")
        if g.description:
            desc = g.description.strip()
            if len(desc) > 400:
                desc = desc[:400] + "..."
            print(f"  Description: {desc}")
        else:
            print("  Description: (none)")
        print()

    print("=" * 60)
    print(f"Total grants found: {total}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
