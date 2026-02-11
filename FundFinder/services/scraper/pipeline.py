import logging

from services.scraper.models import Grant
from services.scraper.sources.base import SourceScraper

logger = logging.getLogger(__name__)


def run_sources(
    scrapers: list[SourceScraper],
    dedupe_by_hash: bool = True,
) -> list[Grant]:
    seen_hashes: set[str] = set()
    results: list[Grant] = []

    for scraper in scrapers:
        try:
            grants = scraper.scrape()
        except Exception as e:
            logger.exception("Source %s failed: %s", scraper.source_name, e)
            continue

        for g in grants:
            if dedupe_by_hash and g.content_hash in seen_hashes:
                continue
            seen_hashes.add(g.content_hash)
            results.append(g)

    return results


def get_all_scrapers() -> list[SourceScraper]:
    """Return production scrapers only. Example/mock scrapers are in services/scraper/examples/."""
    return []
