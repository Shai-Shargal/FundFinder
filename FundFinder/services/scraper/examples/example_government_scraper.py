"""
Example scraper used for educational/demo purposes only.
Not part of the production scraping pipeline.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from services.scraper.models import Grant
from services.scraper.sources.base import SourceScraper
from services.scraper.utils import (
    clean_hebrew_text,
    content_hash,
    parse_deadline,
    utc_now,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "example_government.html"


class ExampleGovernmentScraper(SourceScraper):

    def __init__(self, html_source: str | Path | None = None) -> None:
        super().__init__(
            source_name="example_government",
            base_url="https://example.gov.il/grants",
        )
        self._html_source = html_source

    def scrape(self) -> list[Grant]:
        html = self._load_html()
        soup = BeautifulSoup(html, "html.parser")
        grants: list[Grant] = []

        for idx, item in enumerate(soup.select(".grant-item"), start=1):
            title_el = item.select_one(".grant-title")
            if not title_el:
                continue

            title = clean_hebrew_text(title_el.get_text()) or "Unknown"
            desc_el = item.select_one(".grant-description")
            description = clean_hebrew_text(desc_el.get_text()) if desc_el else None
            deadline_el = item.select_one(".grant-deadline")
            deadline_text = clean_hebrew_text(deadline_el.get_text()) if deadline_el else None
            amount_el = item.select_one(".grant-amount")
            amount = clean_hebrew_text(amount_el.get_text()) if amount_el else None
            eligibility = None

            data_id = item.get("data-id")
            source_url = f"{self.base_url}/{data_id or idx}"

            deadline = parse_deadline(deadline_text) if deadline_text else None

            h = content_hash(
                title=title,
                description=description,
                deadline_text=deadline_text,
                amount=amount,
                eligibility=eligibility,
                source_url=source_url,
            )

            grants.append(
                Grant(
                    title=title,
                    description=description,
                    source_url=source_url,
                    source_name=self.source_name,
                    deadline=deadline,
                    deadline_text=deadline_text,
                    amount=amount,
                    currency="ILS",
                    eligibility=eligibility,
                    content_hash=h,
                    fetched_at=utc_now(),
                    extra=None,
                )
            )

        return grants

    def _load_html(self) -> str:
        source = self._html_source if self._html_source is not None else FIXTURE_PATH

        if isinstance(source, Path):
            return source.read_text(encoding="utf-8")

        if isinstance(source, str):
            potential_path = Path(source)
            if not source.strip().startswith("<") and potential_path.exists():
                return potential_path.read_text(encoding="utf-8")
            return source

        return FIXTURE_PATH.read_text(encoding="utf-8")
