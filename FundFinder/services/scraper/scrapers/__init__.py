from services.scraper.base import SourceScraper
from services.scraper.sources.huji.scraper import HUJIScraper


def get_all_scrapers() -> list[SourceScraper]:
    return [
        HUJIScraper(),
    ]