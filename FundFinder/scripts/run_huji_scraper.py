"""Run the HUJI scraper and print grants found. Fully dynamic—handles any number of grants."""

from __future__ import annotations

import sys

from services.scraper.pipeline import run_sources
from services.scraper.sources.huji.scraper import HUJIScraper


def main() -> None:
    scraper = HUJIScraper()
    print("Running HUJI scraper...")
    print()

    grants = run_sources([scraper])
    total = len(grants)

    print(f"Total grants found: {total}")
    print("-" * 60)

    for i, g in enumerate(grants, 1):
        title = g.title[:70] + "..." if len(g.title) > 70 else g.title
        amount_str = f" | {g.amount}" if g.amount else ""
        print(f"{i:>3}. {title}{amount_str}")

    print("-" * 60)
    print(f"Total grants found: {total}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
