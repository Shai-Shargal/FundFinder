"""Reichman University (IDC Herzliya) scholarships scraper.

Extracts scholarships from the accordion page at
/admissions/undergraduate/scholarships/ using Playwright and BeautifulSoup.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from services.scraper.base import SourceScraper
from services.scraper.models import Grant
from services.scraper.utils import clean_hebrew_text, content_hash, load_page_html, utc_now

logger = logging.getLogger(__name__)

BASE_URL = "https://www.runi.ac.il"
SCHOLARSHIPS_PATH = "/admissions/undergraduate/scholarships/"
SOURCE_NAME = "reichman"
TIMEOUT_MS = 30_000

EXCLUDED_SCHOLARSHIPS = ["ממדים ללימודים"]


def _is_excluded(title: str) -> bool:
    """Return True if the scholarship title matches an excluded entry."""
    normalized = clean_hebrew_text(title)
    if not normalized:
        return False
    for excluded in EXCLUDED_SCHOLARSHIPS:
        if clean_hebrew_text(excluded) == normalized:
            return True
    return False


def _resolve_container(soup: BeautifulSoup, data_target: str) -> tuple[str, object]:
    """
    Resolve data-target (e.g. #scholarDropDown123) to container_id and element.
    Strips leading '#' and uses soup.find(id=container_id).
    Returns (container_id, container_element or None).
    """
    if not data_target or not data_target.strip():
        return ("", None)
    container_id = data_target.strip().lstrip("#").strip()
    if not container_id:
        return ("", None)
    container = soup.find(id=container_id)
    return (container_id, container)


def _extract_item_title(li) -> str | None:
    """Extract title from li: .title element, normalized."""
    title_el = li.select_one(".title")
    if title_el:
        text = title_el.get_text(strip=True)
        if text:
            return clean_hebrew_text(text) or None
    link = li.select_one("a.link")
    if link:
        text = link.get_text(strip=True)
        if text:
            return clean_hebrew_text(text) or None
    return None


def _extract_item_description(li) -> str | None:
    """Extract description from li: p.text element."""
    text_el = li.select_one("p.text")
    if not text_el:
        return None
    text = text_el.get_text(separator=" ", strip=True)
    if not text:
        return None
    return clean_hebrew_text(text) or None


def _make_absolute_url(base_url: str, href: str) -> str:
    """Convert href to absolute URL using page base."""
    if not href or not href.strip():
        return ""
    href = href.strip()
    if href.startswith(("http://", "https://")):
        return href
    return urljoin(base_url, href)


class ReichmanScholarshipSource(SourceScraper):
    """Scrapes Reichman University undergraduate scholarships page."""

    def __init__(self) -> None:
        super().__init__(source_name=SOURCE_NAME, base_url=BASE_URL)

    def scrape(self) -> list[Grant]:
        full_url = urljoin(self.base_url, SCHOLARSHIPS_PATH)
        if not full_url.endswith("/"):
            full_url = full_url.rstrip("/") + "/"
        page_base = full_url

        html = load_page_html(full_url, timeout_ms=TIMEOUT_MS, source_name="Reichman")
        if not html:
            logger.warning("Reichman: no HTML received")
            return []

        soup = BeautifulSoup(html, "html.parser")
        buttons = soup.select("button.btnCollapse")
        if not buttons:
            logger.warning("Reichman: no button.btnCollapse found")
            return []

        grants: list[Grant] = []
        fetched_at = utc_now()
        seen_urls: set[str] = set()

        for button in buttons:
            category = clean_hebrew_text(button.get_text())
            data_target = button.get("data-target")
            if not data_target:
                logger.warning("Reichman: data-target missing, category=%s", category or "(no text)")
                continue

            container_id, container = _resolve_container(soup, data_target)
            # Temporary debug logs
            logger.debug("Reichman: container_id=%s", container_id)
            logger.debug("Reichman: container is None=%s", container is None)
            if container is not None:
                logger.debug("Reichman: container found for id=%s, category=%s", container_id, category)
                preview = container.prettify()[:300] if hasattr(container, "prettify") else str(container)[:300]
                logger.debug("Reichman: container preview (first 300 chars): %s", preview)
            else:
                logger.warning("Reichman: container not found for data-target=%s, container_id=%s, category=%s", data_target, container_id, category)
                continue

            book_list = container.select_one("ul.boxList")
            if not book_list:
                logger.warning("Reichman: no ul.boxList in container, category=%s", category)
                continue

            for li in book_list.find_all("li"):
                link = li.select_one("a.link")
                href = link.get("href") if link else None
                source_url = _make_absolute_url(page_base, href) if href else ""
                title = _extract_item_title(li)

                if not title:
                    logger.warning("Reichman: skipping item with no title (href=%s)", href or "")
                    continue
                if not source_url:
                    logger.warning("Reichman: skipping item with no href, title=%s", title[:50])
                    continue

                normalized_url = source_url.rstrip("/")

                if _is_excluded(title):
                    logger.warning("Reichman: skipping excluded scholarship: %s", title)
                    continue

                if normalized_url in seen_urls:
                    logger.info("Reichman: skipping duplicate URL: %s", normalized_url)
                    continue
                seen_urls.add(normalized_url)

                description = _extract_item_description(li)
                hash_str = content_hash(
                    title=title,
                    description=description,
                    deadline_text=None,
                    amount=None,
                    eligibility=None,
                    source_url=normalized_url,
                )
                grant = Grant(
                    title=title,
                    description=description,
                    source_url=normalized_url,
                    source_name=SOURCE_NAME,
                    deadline=None,
                    deadline_text=None,
                    amount=None,
                    currency=None,
                    eligibility=None,
                    content_hash=hash_str,
                    fetched_at=fetched_at,
                    extra={"category": category} if category else None,
                )
                grants.append(grant)

        logger.info("Reichman: scraped %d grants", len(grants))
        return grants
