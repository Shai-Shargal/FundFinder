#!/usr/bin/env python3
"""
Standalone debug script: fetch and inspect HUJI scholarship Id=460.
Uses the JSON API (scholarshipdetails); web page: scholarships-details?Id=460.
"""

from __future__ import annotations

import json
import sys

if sys.version_info < (3, 11):
    print("This script requires Python 3.11+")
    sys.exit(1)

try:
    import httpx
except ModuleNotFoundError:
    print("Missing dependency: httpx. Use the project venv:")
    print("  cd /path/to/FundFinder && source .venv/bin/activate")
    print("  python -m scripts.debug_huji_scholarship_460")
    sys.exit(1)

# JSON API (same data as scholarships-details?Id=460)
DETAILS_URL = "https://new.huji.ac.il/scholarshipsservices/scholarshipdetails/460"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _get(data: dict[str, object], key: str) -> str | int | float | bool | None:
    v = data.get(key)
    if v is None:
        return None
    return v  # type: ignore[return-value]


def _str_val(v: str | int | float | bool | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def run_validation(data: dict[str, object]) -> None:
    hebrew_name: str | None = _get(data, "hebrewName")
    if hebrew_name is not None and isinstance(hebrew_name, str):
        if "..." in hebrew_name:
            print("ERROR: Title is truncated")
        if '\\"' in hebrew_name:
            print("ERROR: Escaping issue detected")
    if _get(data, "sumYearTo") is None:
        print("WARNING: No structured amount field")
    if _get(data, "submissionDateTo") is None:
        print("INFO: No deadline defined")


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"Fetching {DETAILS_URL} ...")
    resp = httpx.get(DETAILS_URL, headers=HEADERS, timeout=15.0)
    resp.raise_for_status()

    text: str = resp.text or resp.content.decode("utf-8", errors="replace")
    text = text.strip().lstrip("\ufeff")
    if not text:
        print("Empty response.")
        sys.exit(1)

    try:
        data: dict[str, object] = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

    # Fields to print (label, key)
    fields: list[tuple[str, str]] = [
        ("scholarshipsId", "scholarshipsId"),
        ("hebrewName", "hebrewName"),
        ("englishName", "englishName"),
        ("sumYearTo", "sumYearTo"),
        ("sumCurrency", "sumCurrency"),
        ("amountScholarshipsOffered", "amountScholarshipsOffered"),
        ("degree", "degree"),
        ("scholarshipYear", "scholarshipYear"),
        ("isActive", "isActive"),
        ("isPublished", "isPublished"),
        ("submissionDateFrom", "submissionDateFrom"),
        ("submissionDateTo", "submissionDateTo"),
    ]

    print()
    print("=" * 60)
    print("HUJI Scholarship (Id=460)")
    print("=" * 60)
    for label, key in fields:
        val = _get(data, key)
        print(f"  {label:28} {_str_val(val)}")
    print("=" * 60)

    print("\nValidation:")
    run_validation(data)
    print()


if __name__ == "__main__":
    main()
