from services.scraper.base import SourceScraper
from services.scraper.sources.government.miluim import MiluimSource
from services.scraper.sources.huji.scraper import HUJIScraper
from services.scraper.sources.mod.scraper import MODScraper


def get_all_scrapers() -> list[SourceScraper]:
    return [
        HUJIScraper(),
        MODScraper(),
        MiluimSource(),
    ]