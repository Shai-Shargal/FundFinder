"""Playwright-based scraper for Miluim student grant (סיוע חד פעמי) from the article page.

Production-grade implementation with:
- Keyword-based relevant block detection (no exact phrase dependency)
- Contextual amount extraction (fighter vs rear by proximity to לוחם / עורפי)
- Decimal-based amount normalization
- Academic year in Grant.extra
- Fallback to full article text when block extraction fails
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from services.scraper.base import SourceScraper
from services.scraper.models import Grant
from services.scraper.utils import content_hash, utc_now

logger = logging.getLogger(__name__)

# --- Configuration -----------------------------------------------------------

ARTICLE_PATH = "/articles-list/סטודנטים-ממילואים-ללימודים"
BASE_URL = "https://www.miluim.idf.il"
SOURCE_NAME = "government_miluim"
TIMEOUT_MS = 30_000

# Keywords used to detect relevant text blocks (at least MIN_KEYWORDS must appear)
RELEVANT_KEYWORDS = ("שכר", "לימוד", "מילואים", "סיוע", "סטודנט")
MIN_KEYWORDS_FOR_BLOCK = 2

# Context window (chars) around tier keywords when resolving amounts
CONTEXT_WINDOW_CHARS = 200

# Content
ELIGIBILITY = "סטודנטים שביצעו לפחות 60 ימי שמ״פ במסגרת צו 8 במהלך שירות מילואים פעיל."
DESCRIPTION = (
    "סיוע חד פעמי בתשלום שכר לימוד עבור סטודנטים המשרתים במילואים במסגרת חרבות ברזל. "
    "היקף הסיוע תלוי בסוג היחידה (לוחם או עורפי)."
)
TITLE_FIGHTER = "מענק מילואים לסטודנטים – מערך לוחם"
TITLE_REAR = "מענק מילואים לסטודנטים – מערך עורפי"

# Regex: amount in parentheses (e.g. 5,000₪ or 5000.00₪)
AMOUNT_IN_PARENS_RE = re.compile(r"\(([\d,\.]+)\s*₪\)")
# Academic year (Hebrew year abbreviation)
ACADEMIC_YEAR_RE = re.compile(r"תש[\u0590-\u05FF\"׳]{2,6}")


# --- Parsed data (extraction result) -----------------------------------------


@dataclass(frozen=True)
class ParsedGrantData:
    """Structured result of parsing article text."""

    fighter_amount_str: str | None  # normalized string for Grant.amount
    rear_amount_str: str | None
    academic_year: str | None


# --- Amount normalization (Decimal) ------------------------------------------


def _normalize_amount_to_decimal(raw: str) -> Decimal | None:
    """Parse amount string (e.g. '5,000' or '5000.00') to Decimal. No float."""
    if not raw or not raw.strip():
        return None
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _decimal_to_amount_str(value: Decimal | None) -> str | None:
    """Convert Decimal to string form for Grant.amount (no trailing .0)."""
    if value is None:
        return None
    # Integer-looking decimals as int string; otherwise keep as is
    if value == value.to_integral_value():
        return str(int(value))
    return str(value)


# --- Extraction: get text from DOM --------------------------------------------


def _score_block(text: str) -> int:
    """Return number of relevant keywords present in text."""
    if not text or not text.strip():
        return 0
    return sum(1 for kw in RELEVANT_KEYWORDS if kw in text)


def _extract_blocks_from_soup(soup: BeautifulSoup) -> list[tuple[str, int]]:
    """Extract text blocks (p/div) with their keyword scores. Returns [(text, score), ...]."""
    blocks: list[tuple[str, int]] = []
    for tag in soup.find_all(["p", "div"]):
        text = (tag.get_text() or "").strip()
        if len(text) < 20:
            continue
        score = _score_block(text)
        if score >= MIN_KEYWORDS_FOR_BLOCK:
            blocks.append((text, score))
    return blocks


def _get_best_relevant_text(soup: BeautifulSoup) -> str | None:
    """
    Get a single text string from the most relevant block(s).
    If multiple blocks have the same max score, concatenate them (order preserved).
    """
    blocks = _extract_blocks_from_soup(soup)
    if not blocks:
        return None
    max_score = max(s for _, s in blocks)
    best = [t for t, s in blocks if s == max_score]
    return "\n".join(best) if best else None


def _get_full_article_text(soup: BeautifulSoup) -> str:
    """Fallback: full text of the main content area or body."""
    # Prefer main/article; fallback to body
    for selector in ("main", "article", "[role='main']", "body"):
        el = soup.select_one(selector)
        if el:
            return (el.get_text() or "").strip()
    return (soup.get_text() or "").strip()


def _extract_article_text(soup: BeautifulSoup) -> tuple[str, bool]:
    """
    Extract text used for parsing. Returns (text, used_fallback).
    used_fallback is True when keyword-based blocks failed and full article was used.
    """
    primary = _get_best_relevant_text(soup)
    if primary and primary.strip():
        return primary.strip(), False
    full = _get_full_article_text(soup)
    if full:
        logger.warning(
            "MiluimStudentGrant: no keyword-matched block found; using full article text as fallback"
        )
        return full, True
    return "", True


# --- Parsing: text -> structured data ----------------------------------------


def _find_amount_near_keyword(text: str, keyword: str) -> str | None:
    """
    Find the first amount (X₪) in a context window around keyword.
    Returns normalized amount string (no commas), or None.
    """
    idx = text.find(keyword)
    if idx < 0:
        return None
    start = max(0, idx - CONTEXT_WINDOW_CHARS)
    end = min(len(text), idx + len(keyword) + CONTEXT_WINDOW_CHARS)
    window = text[start:end]
    match = AMOUNT_IN_PARENS_RE.search(window)
    if not match:
        return None
    raw = match.group(1).strip()
    dec = _normalize_amount_to_decimal(raw)
    return _decimal_to_amount_str(dec) if dec is not None else None


def _parse_academic_year(text: str) -> str | None:
    """Extract first Hebrew academic year (e.g. תשפ״ה) from text."""
    m = ACADEMIC_YEAR_RE.search(text)
    return m.group(0) if m else None


def _parse_grant_data(text: str) -> ParsedGrantData:
    """
    Parse article text into fighter amount, rear amount, and academic year.
    Amounts are resolved by context (near לוחם / עורפי), not by order.
    """
    fighter_amount_str = _find_amount_near_keyword(text, "לוחם")
    rear_amount_str = _find_amount_near_keyword(text, "עורפי")
    academic_year = _parse_academic_year(text)
    return ParsedGrantData(
        fighter_amount_str=fighter_amount_str,
        rear_amount_str=rear_amount_str,
        academic_year=academic_year,
    )


# --- Grant building ----------------------------------------------------------


def _build_extra(academic_year: str | None) -> dict[str, str] | None:
    """Build Grant.extra dict; None if nothing to store."""
    if not academic_year or not academic_year.strip():
        return None
    return {"academic_year": academic_year.strip()}


def _build_grant(
    title: str,
    amount: str | None,
    source_url: str,
    fetched_at: datetime,
    academic_year: str | None,
) -> Grant:
    """Build a single Grant with shared eligibility, description, and optional extra."""
    extra = _build_extra(academic_year)
    hash_str = content_hash(
        title=title,
        description=DESCRIPTION,
        deadline_text=None,
        amount=amount,
        eligibility=ELIGIBILITY,
        source_url=source_url,
    )
    return Grant(
        title=title,
        source_url=source_url,
        source_name=SOURCE_NAME,
        deadline=None,
        amount=amount,
        currency="ILS",
        eligibility=ELIGIBILITY,
        description=DESCRIPTION,
        content_hash=hash_str,
        fetched_at=fetched_at,
        extra=extra,
    )


def _build_grants_from_parsed(
    parsed: ParsedGrantData,
    source_url: str,
    fetched_at: datetime,
) -> list[Grant]:
    """Build exactly two Grant objects from ParsedGrantData, or empty if amounts missing."""
    if not parsed.fighter_amount_str or not parsed.rear_amount_str:
        logger.warning(
            "MiluimStudentGrant: missing amounts (fighter=%s, rear=%s)",
            parsed.fighter_amount_str,
            parsed.rear_amount_str,
        )
        return []
    return [
        _build_grant(
            TITLE_FIGHTER,
            parsed.fighter_amount_str,
            source_url,
            fetched_at,
            parsed.academic_year,
        ),
        _build_grant(
            TITLE_REAR,
            parsed.rear_amount_str,
            source_url,
            fetched_at,
            parsed.academic_year,
        ),
    ]


# --- Scraper (Playwright + orchestration) ------------------------------------


class MiluimStudentGrantSource(SourceScraper):
    """Scrapes the Miluim article page for student grant amounts (fighter / rear) using Playwright."""

    def __init__(self) -> None:
        super().__init__(source_name=SOURCE_NAME, base_url=BASE_URL)

    def scrape(self) -> list[Grant]:
        source_url = self.base_url + quote(ARTICLE_PATH, safe="/")
        grants: list[Grant] = []

        # 1. Load page with Playwright
        html = _load_page_html(source_url)
        if not html:
            logger.warning("MiluimStudentGrant: failed to load page HTML")
            return []

        # 2. Extraction: get text from DOM (keyword-based or fallback)
        soup = BeautifulSoup(html, "html.parser")
        article_text, used_fallback = _extract_article_text(soup)
        if not article_text:
            logger.warning("MiluimStudentGrant: no article text extracted")
            return []

        if used_fallback:
            logger.warning("MiluimStudentGrant: extraction used full-article fallback")

        # 3. Parsing: text -> ParsedGrantData
        parsed = _parse_grant_data(article_text)

        # 4. Grant building
        fetched_at = utc_now()
        grants = _build_grants_from_parsed(parsed, source_url, fetched_at)

        if grants:
            logger.info(
                "MiluimStudentGrant: scraped %d grants (fighter=%s, rear=%s)",
                len(grants),
                parsed.fighter_amount_str,
                parsed.rear_amount_str,
            )
        return grants


def _load_page_html(url: str) -> str | None:
    """Load URL with Playwright (headless), wait for networkidle, return HTML. Caller owns cleanup."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, timeout=TIMEOUT_MS)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
                return page.content()
            finally:
                browser.close()
    except Exception as e:
        logger.warning("MiluimStudentGrant: Playwright load failed: %s", e)
        return None
