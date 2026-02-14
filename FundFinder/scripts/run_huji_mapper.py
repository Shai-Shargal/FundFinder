from __future__ import annotations

import json
import sys

try:
    import httpx
except ModuleNotFoundError:
    print("Missing dependency: httpx. Use the project venv and run as a module from FundFinder root:")
    print("  cd /path/to/FundFinder")
    print("  source .venv/bin/activate")
    print("  python -m scripts.run_huji_mapper")
    sys.exit(1)

from services.scraper.models import Grant
from services.scraper.sources.huji_mapper import map_huji_json_to_grant

HUJI_DETAILS_URL = "https://new.huji.ac.il/scholarshipsservices/scholarshipdetails/{id}"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def print_grant_debug(grant: Grant) -> None:
    print("\n--- Mapped Grant ---")
    print(grant.model_dump_json(indent=2, ensure_ascii=False))


def main() -> None:
    scholarship_id = int(sys.argv[1]) if len(sys.argv) > 1 else 43
    url = HUJI_DETAILS_URL.format(id=scholarship_id)

    print(f"Fetching {url} ...")
    resp = httpx.get(url, headers=HEADERS, timeout=15.0)
    resp.raise_for_status()

    text = resp.text or resp.content.decode("utf-8", errors="replace")
    text = text.strip().lstrip("\ufeff")
    if not text:
        print(f"Empty response. Status: {resp.status_code}")
        raise SystemExit(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Server returned non-JSON. Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', '?')}")
        print(f"Body snippet:\n{text[:500]}")
        raise SystemExit(1) from e

    grant = map_huji_json_to_grant(data)
    print_grant_debug(grant)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
