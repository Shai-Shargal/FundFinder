# FundFinder — Design Document (PoC)

## 1. Project Overview

- **What it is:** FundFinder is a platform that collects and normalizes scholarship and grant information for Israeli students.
- **Who it is for:** Israeli students (and advisors) who need a single place to discover and compare funding opportunities from government, universities, foundations, and other sources.

## 2. Problem Statement

- Grant and scholarship information is scattered across many Israeli websites (government, universities, NGOs, etc.).
- Each source uses different formats, languages (Hebrew/English), and structures.
- Students waste time checking multiple sites and risk missing deadlines or opportunities.
- There is no unified, normalized view of eligibility, amounts, or deadlines across sources.

FundFinder aims to solve this by aggregating and normalizing grant data into one consistent model so users can search and compare in one place.

## 3. High-Level Architecture

- **Scrapers (sources):** Each scraper is responsible for one data source. It fetches or reads content (e.g. HTML), parses it, and returns a list of grants in the unified data model. Scrapers extend a common base interface.
- **Pipeline:** Orchestrates all registered scrapers, runs them, collects results, and deduplicates by content hash. Failures in one scraper do not stop others.
- **Data model:** A single Grant schema (Pydantic) that all scrapers must produce. This ensures consistent structure and enables comparison and storage later.

## 4. Data Model

- The **Grant** model is the single normalized representation of a funding opportunity. It includes: title, description, source URL, source name, deadline (normalized date and raw text), amount and currency, eligibility, a content hash for deduplication, fetch time, and optional extra fields for source-specific data.
- **Why normalization matters:** Different sites use different date formats, languages, and field names. Mapping everything into one model allows:
  - Deduplication (same grant from different pages or runs).
  - Consistent display and filtering (e.g. by deadline or amount).
  - Change detection over time (via content hash).
- Hebrew text is preserved; the system does not translate or transliterate, only cleans and normalizes for comparison.

## 5. Current State (PoC)

**Implemented:**

- Grant Pydantic model with validation.
- Base scraper interface and pipeline that runs multiple scrapers and deduplicates by content hash.
- Stub scraper that parses a local HTML fixture (example government site) and produces Grant instances.
- Utilities for content hashing, Hebrew-aware text cleaning, and deadline parsing.
- Script to run the pipeline and show grants (e.g. for manual verification).

**Intentionally not yet implemented:**

- No real production website scrapers.
- No database or persistent storage.
- No API or frontend.
- No authentication, scheduling, or deployment.

## 6. Next Steps

- Add one or more real scrapers for live Israeli grant sources (e.g. a government or university site), with respectful rate limiting and error handling.
- Introduce persistent storage (e.g. SQLite or PostgreSQL) to store grants and support simple queries and change detection.
- Expose a minimal API (e.g. REST or GraphQL) so a future frontend or other clients can query grants.
- Optionally add a simple scheduler or CLI entry point to run the pipeline periodically.
- Keep the design document updated as the architecture evolves beyond the PoC.
