"""MOD (Ministry of Defense) "Uniform to Studies" scholarship scraper."""

from __future__ import annotations

import logging
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from services.scraper.base import SourceScraper
from services.scraper.models import Grant
from services.scraper.utils import content_hash, clean_hebrew_text, utc_now

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.hachvana.mod.gov.il/MainEducation/HachvanaScholarship/Pages/UniformToStudies.aspx"
TIMEOUT = 30.0

# Selectors (static HTML)
TITLE_SELECTOR = "h1.lobbylayouttitletext"
CONTENT_SELECTOR = "#ctl00_PlaceHolderMain_displaymodepaneldisplay_ctl01__ControlWrapper_RichHtmlField"

# Patterns for extraction
DEADLINE_ANCHOR = "הרשמה למלגה עד לתאריך"
DEADLINE_PATTERN = re.compile(
    re.escape(DEADLINE_ANCHOR) + r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})"
)
ELIGIBILITY_H3_TEXT = "מי זכאי למלגת"
AMOUNT_PHRASE = "מימון מלא בגובה שכר לימוד אוניברסיטאי"
AMOUNT_FULL_TUITION = "Full university tuition funding"


def _parse_deadline_dd_mm_yyyy(text: str) -> tuple[int, int, int] | None:
    """Extract DD.MM.YYYY after DEADLINE_ANCHOR. Returns (day, month, year) or None."""
    m = DEADLINE_PATTERN.search(text)
    if not m:
        return None
    try:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
            return (day, month, year)
    except (ValueError, IndexError):
        pass
    return None


def _extract_eligibility(container) -> str | None:
    """Find the h3 containing ELIGIBILITY_H3_TEXT, then collect all following sibling
    elements' text until the next h3. Does not include the h3 header text.
    """
    if not container:
        return None
    for h3 in container.find_all("h3"):
        if ELIGIBILITY_H3_TEXT not in (h3.get_text() or ""):
            continue
        parts: list[str] = []
        for sib in h3.next_siblings:
            if hasattr(sib, "name"):
                if sib.name == "h3":
                    break
                if hasattr(sib, "get_text"):
                    t = sib.get_text(" ", strip=True)
                    if t:
                        parts.append(t)
            elif isinstance(sib, str) and sib.strip():
                parts.append(sib.strip())
        if parts:
            return clean_hebrew_text(" ".join(parts)) or None
    return None


class MODScraper(SourceScraper):
    """Scrapes the MOD 'Uniform to Studies' (ממדים ללימודים) scholarship page."""

    def __init__(self) -> None:
        super().__init__(
            source_name="mod",
            base_url="https://www.hachvana.mod.gov.il",
        )

    def scrape(self) -> list[Grant]:
        try:
            resp = httpx.get(SOURCE_URL, timeout=TIMEOUT)
        except httpx.RequestError as e:
            logger.error("MOD: request failed: %s", e)
            return []
        if resp.status_code != 200:
            logger.warning("MOD: non-200 status=%s", resp.status_code)
            return []

        text = resp.text or resp.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(text, "html.parser")

        title_el = soup.select_one(TITLE_SELECTOR)
        container = soup.select_one(CONTENT_SELECTOR)
        if not title_el or not container:
            logger.warning("MOD: title or content container not found")
            return []

        title = clean_hebrew_text(title_el.get_text()) or "Unknown"
        description = container.get_text("\n", strip=True)
        description = clean_hebrew_text(description) or None

        # Deadline: "הרשמה למלגה עד לתאריך" DD.MM.YYYY
        deadline = None
        deadline_text = None
        raw_text = container.get_text(" ", strip=True)
        parsed = _parse_deadline_dd_mm_yyyy(raw_text)
        if parsed:
            day, month, year = parsed
            try:
                deadline = date(year, month, day)
                deadline_text = f"{day:02d}.{month:02d}.{year}"
            except ValueError:
                deadline_text = f"{day}.{month}.{year}"

        # Amount: no fixed numeric amount; optional descriptive text if phrase present
        amount_str: str | None = None
        if AMOUNT_PHRASE in raw_text:
            amount_str = AMOUNT_FULL_TUITION
        currency: str | None = None

        # Eligibility: content under h3 "מי זכאי למלגת" (siblings until next h3)
        eligibility = _extract_eligibility(container)

        hash_str = content_hash(
            title=title,
            description=description,
            deadline_text=deadline_text,
            amount=amount_str,
            eligibility=eligibility,
            source_url=SOURCE_URL,
        )

        grant = Grant(
            title=title,
            description=description,
            source_url=SOURCE_URL,
            source_name="mod",
            deadline=deadline,
            deadline_text=deadline_text,
            amount=amount_str,
            currency=currency,
            eligibility=eligibility,
            content_hash=hash_str,
            fetched_at=utc_now(),
            extra=None,
        )
        logger.info("MOD: scraped 1 grant")
        return [grant]
