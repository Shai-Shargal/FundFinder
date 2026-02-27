Source URL:
https://www.hachvana.mod.gov.il/MainEducation/HachvanaScholarship/Pages/UniformToStudies.aspx

1. Objective

Integrate the Israeli Ministry of Defense “Uniform to Studies” scholarship into FundFinder as a new government-level source.

This scholarship:

Is national and applies across institutions

Is published as a single HTML informational page

Does not expose a listing API

Represents a single logical grant

The goal is to integrate it cleanly without modifying the existing scraper architecture.

2. Source Analysis

After inspecting:

Network tab (Fetch/XHR)

ProcessQuery calls

Response bodies

Page source

We determined:

There is no JSON API

There is no listing endpoint

There are no per-ID detail endpoints

All scholarship content exists directly in the HTML document

Conclusion:

This is a static HTML content-based source.

Therefore:

No need for Playwright / Selenium

No need for JavaScript execution

No need for API reverse engineering

We will use httpx + BeautifulSoup.

3. Architectural Fit

FundFinder uses the contract:

scrape() -> list[Grant]

HUJI is a listing-based source:

Listing → Multiple IDs → Details per ID → Many Grants

MOD is a content-based source:

Single HTML Page → Single Scholarship → One Grant

We will not modify architecture.

Instead:

return [grant]

The pipeline remains unaware that this source behaves differently.

4. Folder Structure
services/
  scraper/
    sources/
      huji/
      mod/
        scraper.py
5. Responsibilities of MODScraper

The scraper will:

Fetch the HTML page

Parse:

Title

Main content / description

Deadline (if available)

Amount (if explicitly stated)

Eligibility information

Normalize into Grant

Return a list with one Grant

6. Data Mapping Strategy
Grant Field	Extraction Strategy
title	Page header (h1 or main heading container)
description	Main content div (full cleaned text)
amount	Extract if numeric pattern exists
currency	ILS (if numeric amount found)
deadline	Extract from text if pattern matches
eligibility	Extract from content text
source_url	Official MOD URL
source_name	"mod"
7. Implementation Strategy
Step 1 – Fetch HTML
html = httpx.get(URL, timeout=30).text
Step 2 – Parse with BeautifulSoup
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
Step 3 – Extract Minimal Required Fields First

Start simple:

Extract title

Extract full text body

Build Grant

Return list with single object

Enhance parsing later if needed.

8. Minimal Viable Scraper (MVP)

Initial implementation should focus only on:

title

description

source_url

source_name

Do NOT over-engineer.

Advanced parsing (deadline / amount extraction) can be added later.

9. Duplicate Handling

Because universities may reference this same scholarship:

FundFinder already deduplicates using:

content_hash

Therefore:

If identical content appears elsewhere

Only one canonical record remains

No extra duplicate logic is needed.

10. Error Handling

If:

Request fails

Page structure changes

Required elements missing

Then:

Log error

Return empty list

Do not crash the pipeline

Fail-safe behavior is required.

11. Example Skeleton
from services.scraper.base import SourceScraper
from services.scraper.models import Grant
import httpx
from bs4 import BeautifulSoup


URL = "https://www.hachvana.mod.gov.il/MainEducation/HachvanaScholarship/Pages/UniformToStudies.aspx"


class MODScraper(SourceScraper):

    def __init__(self) -> None:
        super().__init__(
            source_name="mod",
            base_url="https://www.hachvana.mod.gov.il",
        )

    def scrape(self) -> list[Grant]:
        try:
            response = httpx.get(URL, timeout=30)
            response.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("h1")
        description_container = soup.find("div")  # refine selector later

        if not title or not description_container:
            return []

        grant = Grant(
            title=title.get_text(strip=True),
            description=description_container.get_text(strip=True),
            source_url=URL,
            source_name="mod",
        )

        return [grant]
12. Why This Design Is Correct

✔ No architectural changes
✔ Respects the scrape() -> list[Grant] contract
✔ Works alongside HUJI
✔ Supports heterogeneous source types
✔ Keeps scrapers decoupled
✔ Scales to future government sources

13. Non-Goals
No frontend changes

No DB schema changes

No auto-discovery refactor

No JS execution engine

No Playwright

14. Future Enhancements

Possible improvements:

Structured parsing of deadline patterns

Amount extraction using regex

Eligibility extraction heuristics

Add additional MOD scholarships if discovered

Summary

The MOD “Uniform to Studies” scholarship is a static, content-based source.

It can be integrated cleanly into FundFinder without any architectural modification.

The system now supports:

Listing-based academic sources

Content-based government sources

Multi-ecosystem aggregation
