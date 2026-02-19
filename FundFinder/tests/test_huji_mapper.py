"""Unit tests for HUJI mapper (details payload as source-of-truth)."""

from __future__ import annotations

import pytest

from services.scraper.sources.huji.mapper import map_huji_json_to_grant


# Id=460–style details payload: full title, sumYearTo, no deadline
HUJI_460_MOCK = {
    "scholarshipsId": 460,
    "hebrewName": "מלגות לימודים לתלמידי מוסמך ודוקטור - לשנה\"ל תשפ\"ו",
    "englishName": "Graduate and doctoral scholarships - 2025/26",
    "hebrewDescription": "תיאור המלגה.",
    "englishDescription": None,
    "sumYearTo": 10000,
    "sumCurrency": "ILS",
    "submissionDateFrom": None,
    "submissionDateTo": None,
    "descriptionScholarshipAmount": None,
    "degree": None,
    "nation": None,
    "specialPopulation": None,
    "studyYear": None,
}


def test_map_huji_id460_full_title_amount_no_deadline() -> None:
    """Id=460 mock: full title (no truncation), amount from sumYearTo, deadline None."""
    grant = map_huji_json_to_grant(HUJI_460_MOCK)
    assert grant.title == HUJI_460_MOCK["hebrewName"]
    assert "..." not in grant.title
    assert grant.amount == "10000"
    assert grant.currency == "ILS"
    assert grant.deadline is None
    assert grant.deadline_text is None
    assert "460" in grant.source_url


def test_map_huji_prefers_non_truncated_title() -> None:
    """When hebrewName is truncated, prefer englishName if it is not."""
    payload = {
        **HUJI_460_MOCK,
        "hebrewName": "מלגות לימודים ... לתלמידי מוסמך",
        "englishName": "Full English Title",
    }
    grant = map_huji_json_to_grant(payload)
    assert grant.title == "Full English Title"
    assert "..." not in grant.title


def test_map_huji_amount_from_sum_year_to_zero_uses_description() -> None:
    """When sumYearTo is 0 or missing, amount can come from description text."""
    payload = {
        **HUJI_460_MOCK,
        "sumYearTo": 0,
        "sumCurrency": None,
        "descriptionScholarshipAmount": '5,000 ש"ח',
    }
    grant = map_huji_json_to_grant(payload)
    assert grant.amount == '5,000 ש"ח'
    assert grant.currency in ("ILS", None)


def test_map_huji_title_never_contains_amount_or_truncation() -> None:
    """Regression: Grant.title has no '...' and amount is only in grant.amount (not in title)."""
    grant = map_huji_json_to_grant(HUJI_460_MOCK)
    assert "..." not in grant.title
    assert grant.amount == "10000"
    assert grant.amount not in grant.title
