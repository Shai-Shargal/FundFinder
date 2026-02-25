from __future__ import annotations

import re

from ...models import Grant
from ...utils import content_hash, utc_now, parse_deadline, clean_hebrew_text


def _get(data: dict, key: str, default: str | None = None) -> str | None:
    v = data.get(key)
    if v is None:
        return default
    if isinstance(v, str):
        return v.strip() or default
    return str(v).strip() if v else default


def _first_contact_phone(contacts: list | None) -> str | None:
    if not contacts or not isinstance(contacts, list):
        return None
    first = contacts[0] if contacts else None
    if not isinstance(first, dict):
        return None
    phone = first.get("contactPhone")
    return (phone.strip() if isinstance(phone, str) and phone.strip() else None) or None


# Only match amounts that are clearly money-related (ש"ח, ₪, or explicit phrases).
# Do NOT match bare 4+ digit numbers (years, internal IDs).
_AMOUNT_NUMERIC_PATTERNS = [
    # Range: 5,000–10,000 ש"ח or 5,000 - 10,000 ש"ח (must come before single-amount patterns)
    re.compile(r'\d{1,3}(?:,\d{3})*\s*[-–]\s*\d{1,3}(?:,\d{3})*\s*ש"ח'),
    re.compile(r'\d+\s*[-–]\s*\d+\s*ש"ח'),
    # Number + ש"ח (comma-separated or plain)
    re.compile(r'\d{1,3}(?:,\d{3})*\s*ש"ח'),
    re.compile(r'\d+\s*ש"ח'),
    # ₪ + number
    re.compile(r'₪\s*\d{1,3}(?:,\d{3})*'),
    re.compile(r'₪\s*\d+'),
]
_AMOUNT_PHRASES = ("שכר לימוד מלא", "מלגה מלאה")


def extract_amount(text: str | None) -> str | None:
    if not text or not text.strip():
        return None
    t = text.strip()
    numeric_matches: list[str] = []
    for pat in _AMOUNT_NUMERIC_PATTERNS:
        for m in pat.findall(t):
            s = (m.strip() if isinstance(m, str) else str(m).strip())
            if s and s not in numeric_matches:
                numeric_matches.append(s)
    # Drop matches that are substrings of another (e.g. "10,000 ש"ח" inside "5,000 - 10,000 ש"ח")
    numeric_matches = [
        m for m in numeric_matches
        if not any(m != other and m in other for other in numeric_matches)
    ]
    phrase_found: str | None = None
    for phrase in _AMOUNT_PHRASES:
        if phrase in t:
            phrase_found = phrase
            break
    if numeric_matches and phrase_found:
        return " - ".join(numeric_matches) + " - " + phrase_found
    if numeric_matches:
        return " - ".join(numeric_matches)
    if phrase_found:
        return phrase_found
    return None


def _safe_numeric(data: dict, key: str) -> int | float | None:
    v = data.get(key)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return int(v) if isinstance(v, str) and v.strip().isdigit() else float(v)
    except (TypeError, ValueError):
        return None


def map_huji_json_to_grant(data: dict) -> Grant:
    if not isinstance(data, dict):
        data = {}

    # Title from details only: hebrewName (preferred) else englishName. Never append amount to title.
    hebrew_name = _get(data, "hebrewName")
    english_name = _get(data, "englishName")
    if hebrew_name and "..." not in hebrew_name:
        title = hebrew_name
    elif english_name and "..." not in english_name:
        title = english_name
    else:
        title = hebrew_name or english_name or "Unknown"

    description = _get(data, "hebrewDescription") or _get(data, "englishDescription")

    scholarships_id = data.get("scholarshipsId")
    source_url = (
        f"https://new.huji.ac.il/scholarships-details?Id={scholarships_id}"
        if scholarships_id is not None
        else "https://new.huji.ac.il/scholarships-details?Id=0"
    )

    submission_date_to = _get(data, "submissionDateTo")
    deadline_text = submission_date_to
    deadline = parse_deadline(submission_date_to) if submission_date_to else None

    # Amount: from sumYearFrom and/or sumYearTo; if both equal -> single value, else range; else fallback to description text
    sum_year_from = _safe_numeric(data, "sumYearFrom")
    sum_year_to = _safe_numeric(data, "sumYearTo")
    sum_currency = _get(data, "sumCurrency")
    from_ok = sum_year_from is not None and sum_year_from > 0
    to_ok = sum_year_to is not None and sum_year_to > 0
    if from_ok or to_ok:
        if from_ok and to_ok:
            lo, hi = min(sum_year_from, sum_year_to), max(sum_year_from, sum_year_to)
            amount = str(int(lo)) if lo == int(lo) else str(lo)
            if lo != hi:
                amount += "\u2013" + (str(int(hi)) if hi == int(hi) else str(hi))  # en dash
        elif from_ok:
            amount = str(int(sum_year_from)) if sum_year_from == int(sum_year_from) else str(sum_year_from)
        else:
            amount = str(int(sum_year_to)) if sum_year_to == int(sum_year_to) else str(sum_year_to)
        currency = sum_currency  # as-is, only when we have numeric amount
    else:
        raw_amount_desc = _get(data, "descriptionScholarshipAmount")
        amount = extract_amount(raw_amount_desc)
        if amount is None and description:
            amount = extract_amount(description)
        currency = None  # fallback branch: no numeric amount

    raw_amount_desc = _get(data, "descriptionScholarshipAmount")

    parts = [
        _get(data, "degree"),
        _get(data, "nation"),
        _get(data, "specialPopulation"),
        _get(data, "studyYear"),
    ]
    combined = " | ".join(p for p in parts if p)
    eligibility_raw = clean_hebrew_text(combined).strip() if combined else ""
    eligibility = eligibility_raw or None

    hash_str = content_hash(
        title=title,
        description=description,
        deadline_text=deadline_text,
        amount=amount,
        eligibility=eligibility,
        source_url=source_url,
    )

    extra = {
        "scholarship_type": data.get("scholarshipType"),
        "academic_year_text": data.get("scholarshipYear"),
        "academic_year_en": data.get("scholarshipYearEn"),
        "is_active": data.get("isActive"),
        "frequency": data.get("frequency"),
        "funding_factor": data.get("fundingFactorName"),
        "contact_phone": _first_contact_phone(data.get("scholarshipsContacts")),
        "submission_link": _get(data, "link"),
        "amount_description": raw_amount_desc,
    }
    extra = {k: v for k, v in extra.items() if v is not None}

    return Grant(
        title=title,
        description=description or None,
        source_url=source_url,
        source_name="huji",
        deadline=deadline,
        deadline_text=deadline_text,
        amount=amount,
        currency=currency,
        eligibility=eligibility,
        content_hash=hash_str,
        fetched_at=utc_now(),
        extra=extra if extra else None,
    )
