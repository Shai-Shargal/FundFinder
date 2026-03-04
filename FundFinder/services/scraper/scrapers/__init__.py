from services.scraper.base import SourceScraper
from services.scraper.sources.government import MiluimStudentGrantSource
from services.scraper.sources.huji.scraper import HUJIScraper
from services.scraper.sources.mod.scraper import MODScraper
from services.scraper.sources.reichman.scraper import ReichmanScholarshipSource


def get_all_scrapers() -> list[SourceScraper]:
    return [
        HUJIScraper(),
        MODScraper(),
        MiluimStudentGrantSource(),
        ReichmanScholarshipSource(),
    ]