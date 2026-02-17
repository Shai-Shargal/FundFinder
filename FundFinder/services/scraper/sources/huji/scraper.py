"""HUJI scholarship scraper - fetches all scholarships from the listing endpoint."""

from __future__ import annotations

import json
import logging

import httpx

from services.scraper.base import SourceScraper
from services.scraper.models import Grant

from .mapper import map_huji_json_to_grant

logger = logging.getLogger(__name__)

HUJI_LISTING_URL = "https://new.huji.ac.il/scholarshipsservices/scholarshipsdata"
DEFAULT_TIMEOUT = 30.0
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class HUJIScraper(SourceScraper):
    """Scrapes all HUJI scholarships from the listing API."""

    def __init__(self) -> None:
        super().__init__(source_name="huji", base_url="https://new.huji.ac.il")

    def scrape(self) -> list[Grant]:
        grants: list[Grant] = []
        try:
            resp = httpx.get(
                HUJI_LISTING_URL,
                headers=HEADERS,
                timeout=DEFAULT_TIMEOUT,
            )
        except httpx.TimeoutException as e:
            logger.error("HUJI scrape timed out after %s seconds: %s", DEFAULT_TIMEOUT, e)
            return grants
        except httpx.RequestError as e:
            logger.error("HUJI scrape request failed: %s", e)
            return grants

        if resp.status_code != 200:
            logger.error(
                "HUJI scrape got non-200 response: status=%s, url=%s",
                resp.status_code,
                HUJI_LISTING_URL,
            )
            return grants

        text = resp.text or resp.content.decode("utf-8", errors="replace")
        text = text.strip().lstrip("\ufeff")
        if not text:
            logger.warning("HUJI scrape returned empty body")
            return grants

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("HUJI scrape got invalid JSON: %s", e)
            return grants

        if not isinstance(data, dict):
            logger.warning("HUJI scrape: root is not a dict")
            return grants

        results = data.get("results")
        if results is None:
            logger.warning("HUJI scrape: missing 'results' key")
            return grants
        if not isinstance(results, list):
            logger.warning("HUJI scrape: 'results' is not a list")
            return grants

        for item in results:
            if not isinstance(item, dict):
                logger.debug("HUJI: skipping non-dict item %r", type(item))
                continue
            try:
                grant = map_huji_json_to_grant(item)
                grants.append(grant)
            except Exception as e:
                logger.warning("HUJI: failed to map item %r: %s", item.get("scholarshipsId"), e)

        return grants
