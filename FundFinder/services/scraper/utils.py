
import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

RTL_LTR_MARKS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"

RTL_CHAR_RANGES = [
    (0x0590, 0x05FF),
    (0xFB1D, 0xFB4F),
]


def _is_rtl_char(c: str) -> bool:
    if not c:
        return False
    o = ord(c)
    return any(lo <= o <= hi for lo, hi in RTL_CHAR_RANGES)


def is_rtl(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    rtl_count = sum(1 for c in letters if _is_rtl_char(c))
    return rtl_count > len(letters) / 2


def rtl_display(text: str | None) -> str:
    if text is None or not text.strip():
        return text or ""
    s = text.strip()
    return s[::-1] if is_rtl(s) else s


def display_value(value: str | None | date | datetime | dict | list | Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return str(value)
    if isinstance(value, (dict, list)):
        try:
            s = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            s = str(value)
        return rtl_display(s)
    return rtl_display(str(value))


def content_hash(
    title: str,
    description: str | None,
    deadline_text: str | None,
    amount: str | None,
    eligibility: str | None,
    source_url: str,
) -> str:
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
    if text is None:
        return ""
    s = text.strip()
    s = re.sub(r"\s+", " ", s)
    for mark in RTL_LTR_MARKS:
        s = s.replace(mark, "")
    return s.strip()


def parse_deadline(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    raw = clean_hebrew_text(raw)

    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$", raw)
    if m:
        d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mon, d)
        except ValueError:
            pass

    m = re.match(r"^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$", raw)
    if m:
        y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mon, d)
        except ValueError:
            pass

    return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def retry_network(
    *exceptions: type[BaseException],
    attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
):
    excs = exceptions if exceptions else (Exception,)
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(*excs),
        reraise=True,
    )
