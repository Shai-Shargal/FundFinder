"""Run the HUJI scraper and print grants found. Fully dynamic—handles any number of grants."""

from __future__ import annotations

import logging
import sys

from services.scraper.pipeline import run_sources
from services.scraper.sources.huji.scraper import HUJIScraper

# Show scraper warnings (e.g. listing missing 'results', details non-200)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# Uncomment to see all HUJI debug logs:
# logging.getLogger("services.scraper.sources.huji.scraper").setLevel(logging.DEBUG)


def main() -> None:
    scraper = HUJIScraper()
    print("Running HUJI scraper...")
    print()

    grants = run_sources([scraper])
    total = len(grants)

    print(f"Total grants found: {total}")
    print("-" * 60)

    # Print only "<index>. <title>" (clean list; no amount/deadline etc.)
    for i, g in enumerate(grants, 1):
        print(f"{i:>3}. {g.title}")

    print("-" * 60)
    print(f"Total grants found: {total}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
