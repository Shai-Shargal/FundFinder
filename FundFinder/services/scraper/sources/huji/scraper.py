"""HUJI scholarship scraper - listing for IDs, details endpoint for full data."""

from __future__ import annotations

import json
import logging
import time

import httpx

from services.scraper.base import SourceScraper
from services.scraper.models import Grant

from .mapper import map_huji_json_to_grant

logger = logging.getLogger(__name__)

HUJI_LISTING_URL = "https://new.huji.ac.il/scholarshipsservices/scholarshipsdata"
HUJI_DETAILS_URL = "https://new.huji.ac.il/scholarshipsservices/scholarshipdetails/{id}"
DEFAULT_TIMEOUT = 30.0
DETAILS_TIMEOUT = 15.0
DETAILS_RETRY_DELAY = 2.0
# Browser-like headers so the listing endpoint returns JSON (it returns HTML for bare requests)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://new.huji.ac.il/scholarships",
    "Origin": "https://new.huji.ac.il",
    "Accept-Language": "en-US,en;q=0.9,he;q=0.8",
}


def _fetch_details(client: httpx.Client, scholarship_id: int) -> dict | None:
    url = HUJI_DETAILS_URL.format(id=scholarship_id)
    for attempt in range(2):
        try:
            resp = client.get(url, headers=HEADERS, timeout=DETAILS_TIMEOUT)
            if resp.status_code != 200:
                logger.warning(
                    "HUJI: details non-200 for id=%s, status=%s",
                    scholarship_id,
                    resp.status_code,
                )
                return None
            text = resp.text or resp.content.decode("utf-8", errors="replace")
            text = text.strip().lstrip("\ufeff")
            if not text:
                return None
            return json.loads(text)
        except httpx.TimeoutException:
            logger.warning("HUJI: details timeout for id=%s (attempt %s)", scholarship_id, attempt + 1)
            if attempt == 0:
                time.sleep(DETAILS_RETRY_DELAY)
        except (httpx.RequestError, json.JSONDecodeError) as e:
            logger.warning("HUJI: details failed for id=%s: %s", scholarship_id, e)
            return None
    return None


class HUJIScraper(SourceScraper):
    """Scrapes HUJI scholarships: listing for IDs, then details per ID for full data."""

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

        # Listing sometimes returns HTML error page instead of JSON (e.g. "Something went wrong")
        if text.lstrip().startswith("<!") or text.lstrip().lower().startswith("<html"):
            logger.error(
                "HUJI scrape: listing endpoint returned HTML (not JSON). "
                "Server may be blocking the request or the listing URL has changed."
            )
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

        # Deduplicate by ID; listing uses "scholarshipId", details use "scholarshipsId"
        seen_ids: set[int] = set()
        ids_to_fetch: list[int] = []
        for item in results:
            if not isinstance(item, dict):
                logger.debug("HUJI: skipping non-dict item %r", type(item))
                continue
            sid = item.get("scholarshipsId") or item.get("scholarshipId")
            if sid is None:
                continue
            try:
                sid = int(sid)
            except (TypeError, ValueError):
                continue
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            ids_to_fetch.append(sid)

        total_ids = len(ids_to_fetch)
        details_ok = 0
        details_fail = 0

        with httpx.Client() as client:
            for scholarship_id in ids_to_fetch:
                details = _fetch_details(client, scholarship_id)
                if details is None or not isinstance(details, dict):
                    details_fail += 1
                    logger.warning("HUJI: details fetch failed for id=%s (skipped, no fallback to listing)", scholarship_id)
                    continue
                try:
                    grant = map_huji_json_to_grant(details)
                    details_ok += 1
                    grants.append(grant)
                except Exception as e:
                    details_fail += 1
                    logger.warning("HUJI: failed to map details for id=%s: %s", scholarship_id, e)

        logger.info(
            "HUJI: total_ids=%s, details_ok=%s, details_fail=%s, grants=%s",
            total_ids,
            details_ok,
            details_fail,
            len(grants),
        )
        return grants
