
from abc import ABC, abstractmethod

from services.scraper.models import Grant


class SourceScraper(ABC):
  
    source_name: str
    base_url: str

    def __init__(self, source_name: str, base_url: str) -> None:
        self.source_name = source_name
        self.base_url = base_url

    @abstractmethod
    def scrape(self) -> list[Grant]:
        ...
