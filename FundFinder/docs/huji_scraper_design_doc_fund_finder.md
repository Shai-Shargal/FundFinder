# HUJI Scholarships Scraper — Design Document (FundFinder)

## 1) Context
FundFinder already has a working scraping architecture built for learning and for a PoC:
- A **unified data model**: `Grant`
- A **scraper contract**: `SourceScraper` with `scrape() -> list[Grant]`
- A **pipeline** that runs many scrapers and aggregates results
- A **mock scraper** (`ExampleGovernmentScraper`) that parses a local HTML fixture with BeautifulSoup

The mock scraper is **training wheels**: it demonstrates *structure* (how a scraper fits into the pipeline) but not *real-world acquisition*.

We now want a **real HUJI (Hebrew University) scholarships scraper**.

---

## 2) The real problem
### 2.1 Why the mock approach breaks
The mock scraper assumes:
- The data exists in **static HTML** on disk or in the HTML response.
- We can locate the data using **CSS selectors** (e.g., `.grant-item`, `.grant-title`).

HUJI does **not** work that way.

### 2.2 What HUJI actually does
The page a user opens:
- `https://new.huji.ac.il/scholarships-details?Id=43`

is mostly a **shell**. The scholarship content is loaded later via JavaScript.

The actual data comes from a **JSON API endpoint**:
- `https://new.huji.ac.il/scholarshipsservices/scholarshipdetails/43`

So, BeautifulSoup on the page HTML is the wrong tool for the main content.

---

## 3) Bugs we saw (and what they mean)
### 3.1 Hebrew text appearing reversed
You saw outputs like:
- `OG-לִמ תגלמ - ג"למ תגלמ`

That’s a sign that a “cleaning” function is **reversing strings** or mishandling RTL.

**Root cause:** reusing HTML-oriented cleaning logic (`clean_hebrew_text`) on content that’s already clean (JSON text) can break RTL.

**Fix:** for HUJI JSON, we only do safe normalization:
- normalize newlines (`\r\n` -> `\n`)
- trim whitespace
- **no reversing**

### 3.2 Academic year conversion producing nonsense (e.g., 1719)
You saw things like:
- `academic_year_text: "מלגות"`
- `academic_year_gregorian: 1719`

That means “year detection” was too permissive and tried to convert words that are **not** years.

**Root cause:** a “Hebrew year → Gregorian” conversion was applied without strict validation.

**Fix:**
- Prefer HUJI’s own fields: `scholarshipYearEn` like `"2025 - 2026"`
- Only attempt Hebrew-year conversion if there’s a strict match such as `תשפ"ו`.

---

## 4) What we want to extract (MVP)
We define a **minimum viable extraction** so we don’t overbuild.

### 4.1 Required (must-have)
Mapped into `Grant`:
- `title`
- `description`
- `source_url` (canonical details page)
- `source_name = "huji"`
- `content_hash` (stable dedup)
- `fetched_at` (UTC)

### 4.2 Optional (nice-to-have if present)
- `deadline_text` + `deadline` (normalized)
- `amount`
- `currency`
- `eligibility`

### 4.3 Source-specific (goes into `extra`)
We do **not** change the `Grant` schema. We store HUJI-specific metadata in `extra`:
- `apply_url` (HUJI’s submission link)
- `academic_year_text` (e.g., `תשפ"ו 2025-2026`)
- `academic_year_start` (e.g., 2025)
- `is_relevant` (bool)
- `relevance_reason` (string)
- `contacts` (phone/email if present)
- `frequency`, `scholarship_type`, `handle_entity`, etc.

---

## 5) Relevance logic (dynamic, not hardcoded to 2026)
We need the scraper to keep working next year without edits.

### Inputs
- `deadline` if present
- `academic_year_start` (from `scholarshipYearEn`) if present
- optionally `hebrew_academic_year` if found

### Rules (simple + safe)
1) If `deadline` exists and `deadline < today` → **not relevant** (`deadline_passed`)
2) Else if `academic_year_start` exists:
   - If `academic_year_start >= current_year - 1` → **relevant** (`academic_year_match`)
   - Else → **not relevant** (`old_year`)
3) Else → **relevant** (`unknown`)

Why `current_year - 1`?
- Academic years cross years (e.g., 2025–2026 is still relevant in early 2026).

---

## 6) The solution approach
### 6.1 Keep architecture, replace data acquisition
We do **not** rebuild FundFinder.
We keep:
- `SourceScraper` contract
- `Grant` model
- Pipeline (`get_all_scrapers()` / `run_sources()`)

We replace only:
- “read HTML fixture + BeautifulSoup selectors”

with:
- “fetch JSON from HUJI API + map JSON fields to `Grant`”

### 6.2 HUJI scraper responsibilities
A HUJI scraper must:
1) Discover which scholarships exist (IDs)
2) For each ID, fetch details JSON
3) Convert JSON → `Grant`
4) Return list of grants

---

## 7) Endpoint strategy
### 7.1 Confirmed endpoint
- Details (by ID): `GET /scholarshipsservices/scholarshipdetails/{id}`

### 7.2 Still needed
- Listing endpoint (to get all IDs) — best found in browser DevTools Network (Fetch/XHR) when opening:
  - `https://new.huji.ac.il/scholarships`

If listing API exists (likely), we should use it.

### 7.3 Temporary fallback (if listing API is unknown)
Until listing API is found, we can:
- Parse the listing page HTML for `scholarships-details?Id=...` links **if present**
- Or maintain a small seed list / limited probing (not ideal; avoid hammering the site)

---

## 8) Field mapping from HUJI JSON (example: Id=43)
Key fields in JSON:
- `hebrewName`, `englishName`
- `hebrewDescription`, `englishDescription`
- `scholarshipYear`, `scholarshipYearEn`
- `sumCurrency`
- `descriptionScholarshipAmount`
- `degree`, `nation`, `specialPopulation`
- `link` (apply/info)
- `scholarshipsContacts`

Mapping rules:
- `title = hebrewName || englishName || "Unknown"`
- `description = hebrewDescription || englishDescription`
- `currency = sumCurrency || None`
- `eligibility = join([degree, nation, specialPopulation], " | ")`
- `extra.apply_url = link`
- `extra.academic_year_text = scholarshipYear || scholarshipYearEn`
- `extra.academic_year_start = first 20xx found in scholarshipYearEn`

---

## 9) Error handling + robustness
We need scraping to be resilient:
- Timeouts on HTTP calls
- Non-200 responses: skip item, continue
- JSON parse errors: try `.json()`, fallback to `json.loads(text)`
- Missing fields: safe fallbacks (don’t crash)

We prefer “return partial results” over failing the whole run.

---

## 10) Implementation plan (no code yet)
### Step 1 — Validate one scholarship
- Use ID 43
- Fetch JSON from the details endpoint
- Map to `Grant`
- Print/inspect output: ensure Hebrew is not reversed and year parsing is correct

### Step 2 — Identify listing API
- Open `https://new.huji.ac.il/scholarships`
- Network → Fetch/XHR
- Find request returning many scholarships / IDs

### Step 3 — Full scrape
- Fetch list of IDs from listing API
- For each ID fetch details JSON
- Map all to `Grant`

### Step 4 — Relevance filtering (optional)
- Option A: store relevance in `extra` only (recommended)
- Option B: pipeline can later filter by `extra.is_relevant`

---

## 11) Why we keep the mock scraper in the repo
We keep it because:
- It teaches how scrapers plug into the pipeline
- It is useful for tests and for learning

But for HUJI, we do not reuse its HTML/BeautifulSoup logic.

---

## 12) Definition of done
We consider HUJI scraper “done” when:
- It returns valid `Grant` objects from HUJI JSON
- Hebrew text is correct (not reversed)
- Academic year extraction is correct and not nonsense
- Relevance logic updates automatically with today’s date
- Pipeline runs HUJI scraper with no architecture changes

