"""Fetch HUJI grants and show 5 random ones so you can see how the data looks."""

from __future__ import annotations

import logging
import random
import sys

from services.scraper.pipeline import run_sources
from services.scraper.sources.huji.scraper import HUJIScraper

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    scraper = HUJIScraper()
    print("Fetching HUJI grants...")
    grants = run_sources([scraper])
    total = len(grants)
    print(f"Fetched {total} grants. Showing 5 random:\n")

    if total == 0:
        print("No grants to show.")
        return

    sample_size = min(5, total)
    chosen = random.sample(grants, sample_size)

    for i, g in enumerate(chosen, 1):
        desc_preview = (g.description[:200] + "…") if g.description and len(g.description) > 200 else (g.description or "—")
        print("=" * 60)
        print(f"Grant {i}")
        print("=" * 60)
        print("title:       ", g.title)
        print("amount:      ", g.amount or "—")
        print("currency:    ", g.currency or "—")
        print("deadline:    ", g.deadline or g.deadline_text or "—")
        print("eligibility: ", (g.eligibility or "—")[:80])
        print("source_url:  ", g.source_url)
        print("description: ", desc_preview)
        if g.extra:
            extra_preview = {k: v for k, v in list(g.extra.items())[:3]}
            print("extra (sample):", extra_preview)
        print()

    print("=" * 60)
    print(f"Total fetched: {total}  |  Shown: {sample_size}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
