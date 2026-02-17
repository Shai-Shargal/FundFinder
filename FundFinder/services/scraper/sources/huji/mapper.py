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


_AMOUNT_NUMERIC_PATTERNS = [
    re.compile(r'\d{1,3}(?:,\d{3})*\s?ש"ח'),
    re.compile(r'₪\s?\d{1,3}(?:,\d{3})*'),
    re.compile(r'\d{4,}'),
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


def map_huji_json_to_grant(data: dict) -> Grant:
    if not isinstance(data, dict):
        data = {}

    title = _get(data, "hebrewName") or _get(data, "englishName") or "Unknown"
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

    raw_amount_desc = _get(data, "descriptionScholarshipAmount")
    amount = extract_amount(raw_amount_desc)
    if amount is None and description:
        amount = extract_amount(description)
    sum_currency = _get(data, "sumCurrency")
    if sum_currency:
        currency = sum_currency
    elif amount:
        currency = "ILS"
    else:
        currency = None

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
