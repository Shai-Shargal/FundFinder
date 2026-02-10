"""Scraper utilities: content_hash, retries, Hebrew-aware text, date parsing.

Do not translate or transliterate Hebrew; preserve original meaning.
"""

import hashlib
import re
from datetime import date, datetime, timezone

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# RTL/LTR Unicode marks; strip only if they cause comparison issues (documented).
RTL_LTR_MARKS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"

def rtl_display(text: str | None) -> str:
    """Reverse RTL text for terminal display so Hebrew reads correctly left-to-right.

    Terminals that don't support Unicode bidi show Hebrew in wrong order. Reversing
    the string makes it display in the correct reading order when the terminal
    renders LTR.
    """
    if text is None or not text.strip():
        return text or ""
    return text.strip()[::-1]


def content_hash(
    title: str,
    description: str | None,
    deadline_text: str | None,
    amount: str | None,
    eligibility: str | None,
    source_url: str,
) -> str:
    """Stable hash for deduplication and change detection.

    Same content (after normalization) yields the same hash.
    Uses UTF-8 and SHA-256.
    """
    parts = [
        title or "",
        description or "",
        deadline_text or "",
        amount or "",
        eligibility or "",
        source_url or "",
    ]
    normalized = "|".join(clean_hebrew_text(p).strip() for p in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_hebrew_text(text: str | None) -> str:
    """Hebrew-aware text cleaning: strip and normalize spaces only.

    Does NOT translate or transliterate. Optional: strip RTL/LTR marks
    if they cause comparison issues (e.g. in content_hash).
    """
    if text is None:
        return ""
    s = text.strip()
    # Normalize internal whitespace (including newlines/tabs) to single space.
    s = re.sub(r"\s+", " ", s)
    # Optionally strip RTL/LTR marks for stable comparison; document in code.
    for mark in RTL_LTR_MARKS:
        s = s.replace(mark, "")
    return s.strip()


def parse_deadline(raw: str | None) -> date | None:
    """Parse deadline from multiple formats (dd/mm/yyyy, Hebrew months, textual).

    Returns None if unclear; caller should keep raw string in deadline_text.
    TODO: business rules ambiguous for phrases like "until 15.3" vs "application by 15.3".
    """
    if not raw or not raw.strip():
        return None
    raw = clean_hebrew_text(raw)

    # dd/mm/yyyy or d/m/yyyy
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$", raw)
    if m:
        d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mon, d)
        except ValueError:
            pass

    # yyyy-mm-dd
    m = re.match(r"^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$", raw)
    if m:
        y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mon, d)
        except ValueError:
            pass

    # TODO: Hebrew month names (e.g. תשרי, חשון) and phrases like "עד סוף סמסטר".
    return None


def utc_now() -> datetime:
    """Current time in UTC for fetched_at."""
    return datetime.now(timezone.utc)


def retry_network(
    *exceptions: type[BaseException],
    attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
):
    """Tenacity retry decorator for network/parsing; exponential backoff.

    Use for httpx requests and parsing. Fail gracefully at call site
    (log, return empty list or raise clear exception per policy).
    """
    excs = exceptions if exceptions else (Exception,)
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(*excs),
        reraise=True,
    )
