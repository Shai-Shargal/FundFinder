# Reichman University Scholarships Scraper — Technical Design

## 1. Scope

This document defines the **technical design** for a production-grade scraper that extracts scholarships from Reichman University (IDC Herzliya) at:

**URL:** `https://www.runi.ac.il/admissions/undergraduate/scholarships/`

- **In scope:** Reichman University only. No other institutions, no LLM-based extraction, no beta or generic scraping frameworks.
- **Goal:** Extract all listed scholarships (internal and external), preserve category, exclude only the scholarship titled "ממדים ללימודים", and keep external scholarships (e.g., Telfed).

---

## 2. Architecture Overview

### 2.1 High-level flow

1. **Load** the scholarships page with Playwright (headless).
2. **Wait** for a stable load state (e.g. `networkidle` or `domcontentloaded` + short delay) so that accordion markup is present in the DOM.
3. **Capture** the full HTML via `page.content()`.
4. **Parse** the HTML with BeautifulSoup (no further browser interaction).
5. **Extract** all accordion sections, then for each section extract list items and build one `Grant` per scholarship link (subject to exclusion).
6. **Return** `list[Grant]` from `scrape()`.

### 2.2 Playwright usage

- **Role:** Load the page and execute any page JavaScript so that the final DOM (including accordion structure and list items) is available.
- **Browser:** Chromium, headless.
- **Single navigation:** One `goto(scholarships_url)`; no multi-step navigation.
- **Cleanup:** Browser must be closed in a `finally` block after capturing HTML.

Playwright is used only for **acquisition** of the rendered HTML. All parsing and extraction are done in process using BeautifulSoup.

### 2.3 HTML parsing with BeautifulSoup

- **Input:** HTML string returned by Playwright.
- **Parser:** `html.parser` (or equivalent) via BeautifulSoup.
- **No HTTP in parsing layer:** Parsing logic does not perform requests; it operates only on the HTML string.

All selectors and traversal (buttons, containers, `ul.bookList`, `li`, links, text) are expressed as BeautifulSoup queries on this tree.

### 2.4 Why no click interaction is required

The page is structured as an **accordion** (collapse sections). For this design we assume that:

- After the page has fully loaded (and optional wait for network idle), **all accordion panels are already present in the DOM**.
- Visibility of each panel is controlled by **CSS/attributes** (e.g. `display: none`, `aria-expanded`, or similar), not by lazy-loading of content on first click.

Therefore, the entire list of scholarships is available in the initial DOM. The scraper can:

1. Find all `button.btnCollapse` elements.
2. For each button, resolve the container via `data-target` (or equivalent).
3. Within each container, find `ul.bookList` and iterate `li` elements.

No programmatic clicks are required. If a future version of the site lazy-loads panel content on expand, the design would need to be updated to add a click-and-wait step per section; that is out of scope for this document.

### 2.5 Grant creation process

- One **Grant** is created per scholarship link (per `<li>` that contains an `<a class="link">` with `href` and meaningful title).
- **Exclusion:** Scholarships whose title matches the exclusion list (see §4) are not turned into grants; they are skipped and logged.
- **Category:** The accordion section title (button text) is stored as `extra["category"]` on each grant.
- **Stability:** Each grant gets a `content_hash` (see §5) and `fetched_at` (UTC) for deduplication and pipeline consistency.

---

## 3. Extraction Strategy

### 3.1 Locate all accordion buttons

- **Selector:** `button.btnCollapse` (elements that have both the `button` tag and the class `btnCollapse`).
- **Method:** `soup.select("button.btnCollapse")` or equivalent.
- **Result:** Ordered list of button elements. Each button represents one scholarship category.

### 3.2 Extract category name from button text

- **Source:** The visible text of the button (e.g. `button.get_text(strip=True)` or equivalent).
- **Normalization:** Trim whitespace and normalize internal whitespace (e.g. collapse newlines to spaces). No RTL reversal.
- **Use:** This string is the **category** for every scholarship extracted from the corresponding container (e.g. "מלגות פנימיות", "מלגות חיצוניות", or provider names like "תלפיד").

### 3.3 Resolve related container via `data-target`

- **Attribute:** Each `button.btnCollapse` has a `data-target` attribute (or similar) that references the ID (or selector) of the expandable container.
- **Resolution:**
  - Read `data-target` from the button (e.g. `#panel-1` or `.panel-1`).
  - If it is an ID (e.g. `#panel-1`), find the element with that ID: `soup.find(id="panel-1")` (strip the `#`).
  - If it is a class or other selector, use `soup.select_one(value_of_data_target)`.
- **Fallback:** If the container is not found for a given button, log a warning and skip that category; do not fail the whole scrape.

### 3.4 Iterate over `ul.bookList` and `li`

- **Container:** For each resolved accordion panel, find within it a `ul` with class `bookList` (and optionally `row`): e.g. `container.select_one("ul.bookList")` or `container.find("ul", class_="bookList")`.
- **Items:** Select all direct or descendant `li` elements: e.g. `book_list.select("li")` or `book_list.find_all("li")`.
- **Per item:** Look for a single anchor with class `link` and a `href`; extract title and optional description from the structure below (e.g. `div.textContainer`).

### 3.5 Extract fields per scholarship

| Field         | Source | Notes |
|---------------|--------|--------|
| **title**     | Link text or `div.textContainer` title element | Primary display name; used for exclusion and display. Trim and normalize whitespace. |
| **href**      | `a.link["href"]` | Resolve to absolute URL using the page base URL (e.g. `https://www.runi.ac.il`) so `source_url` is canonical. |
| **description** | Text inside `div.textContainer` (excluding or in addition to title, depending on DOM) | Optional; may be empty. Stored in `Grant.description`. |
| **category**  | Button text from the accordion section (see 3.2) | Stored in `Grant.extra["category"]`. |

- **source_url:** The absolute scholarship link (same as resolved `href`).
- **source_name:** Constant `"reichman"` (or agreed project identifier) for this scraper.
- **deadline / amount / currency / eligibility:** Filled only if present on the list page or in the link snippet; otherwise `None`. No scraping of detail pages is required for MVP.

---

## 4. Exclusion Logic

### 4.1 Design principle

We exclude **only** scholarships whose title exactly or nearly matches a known list. This keeps the scraper simple and predictable: one source of truth for exclusions (title), no dependency on category or URL.

### 4.2 EXCLUDED_SCHOLARSHIPS list

Define a module-level (or class-level) constant:

- **EXCLUDED_SCHOLARSHIPS:** A list of exact or canonical titles to exclude.  
  **Minimum content:** `["ממדים ללימודים"]`  
  Additional entries may be added if product requires excluding other titles (e.g. test or duplicate entries).

### 4.3 _is_excluded(title: str)

- **Input:** Normalized scholarship title (trimmed, whitespace collapsed).
- **Logic:** Return `True` if the title equals (or matches after normalization) any entry in `EXCLUDED_SCHOLARSHIPS`. Matching may be exact string equality or case-insensitive / diacritic-insensitive comparison, as long as it is documented and consistent.
- **Use:** Before creating a `Grant`, call `_is_excluded(title)`. If `True`, skip this item and log (see 4.4).

### 4.4 Why exclusion is based on title

- **Stability:** Titles are the primary user-visible identifier and are less likely to change than URLs or internal IDs.
- **Simplicity:** No need to maintain URL patterns or category-based rules; one list of titles suffices.
- **Explicit:** Product can add or remove titles without touching extraction logic.

### 4.5 Logging skipped scholarships

When a scholarship is skipped because it is excluded:

- Log at **warning** level with a clear message, e.g. `"Reichman: skipping excluded scholarship: <title>"`.
- Do not increment the grant count for that item; it does not appear in the returned `list[Grant]`.

---

## 5. Data Model

### 5.1 Grant object (example)

The scraper returns the same `Grant` model used by other FundFinder sources. Example for one Reichman scholarship:

```text
Grant(
    title="מלגת תלפיד",
    description="תיאור קצר אם קיים בעמוד הרשימה",
    source_url="https://www.runi.ac.il/...",
    source_name="reichman",
    deadline=None,
    deadline_text=None,
    amount=None,
    currency=None,
    eligibility=None,
    content_hash="<sha256 from content_hash(...)>",
    fetched_at=datetime(..., tzinfo=timezone.utc),
    extra={"category": "מלגות חיצוניות"}
)
```

### 5.2 extra["category"]

- **Key:** `"category"`.
- **Value:** The accordion section title (button text) for the section from which this scholarship was extracted.
- **Purpose:** Enables filtering or display by category (internal vs external, or by provider) without changing the global `Grant` schema.

### 5.3 API consistency

- **Scraper class:** Subclass of `SourceScraper` with `source_name` and `base_url` set in `__init__`.
- **Entry point:** `scrape() -> list[Grant]`; no change to the public API of other scrapers.
- **content_hash:** Built using the same `content_hash` utility as other sources (title, description, deadline_text, amount, eligibility, source_url).

---

## 6. Deduplication Strategy

### 6.1 content_hash

- **Inputs:** The same fields used elsewhere: `title`, `description`, `deadline_text`, `amount`, `eligibility`, `source_url`. Optional: include `extra["category"]` in the hashed string if the product wants category to affect identity (e.g. same title in two categories = two grants). Document the choice.
- **Output:** A stable string (e.g. SHA-256 hex) stored in `Grant.content_hash`.
- **Use:** The pipeline (or downstream) can deduplicate by `content_hash` so the same scholarship is not stored twice across runs or across sources.

### 6.2 Preventing duplicates across sources

- **Same source (Reichman):** Two list items with the same `source_url` and same title/description will produce the same `content_hash`, so they are treated as one grant.
- **Cross-source:** If another scraper (e.g. MOD) also lists "מלגת X", the hashes will differ because `source_url` (and possibly `source_name`) differ. The pipeline may keep both and rely on downstream logic or UI to merge or label by source.

No extra deduplication logic is required inside the Reichman scraper beyond computing `content_hash` per grant.

---

## 7. Robustness Considerations

### 7.1 Missing containers

- If **no** `button.btnCollapse` is found: Log a warning and return an empty list (or a list of grants from other discovery paths if any exist).
- If **a** button has no matching container for its `data-target`: Log a warning including the button text or index, skip that category, continue with others.
- If a container has **no** `ul.bookList`: Log a warning for that category, skip it, continue.

### 7.2 Unexpected DOM changes

- If the site changes class names or structure:
  - Prefer **defensive** selection: e.g. check for `None` after `select_one` / `find` before accessing children.
  - Log **warnings** when expected elements are missing (e.g. "Reichman: no ul.bookList in container for category X").
- Avoid hard assumptions about exact nesting (e.g. "second div inside textContainer"); prefer the minimal selector that yields title and description.

### 7.3 Logging

- **Info:** Number of grants extracted (e.g. "Reichman: scraped N grants").
- **Warning:** Fallback or anomaly: no buttons found, container not found, no bookList, excluded scholarship skipped, missing title/href for an item.
- **Error:** Only for unrecoverable failures (e.g. Playwright cannot load the page). Prefer returning an empty list and logging rather than raising, so the pipeline can continue with other sources.

---

## 8. Summary

| Aspect | Decision |
|--------|----------|
| **Source** | Reichman University scholarships page only |
| **Acquisition** | Playwright (headless), single page load |
| **Parsing** | BeautifulSoup on full HTML; no clicks |
| **Structure** | Accordion: `button.btnCollapse` → `data-target` → container → `ul.bookList` → `li` → `a.link` + `div.textContainer` |
| **Exclusion** | Title-based list; exclude "ממדים ללימודים"; log skipped |
| **Category** | From button text → `extra["category"]` |
| **Deduplication** | `content_hash` utility; pipeline-level dedup |
| **Output** | `scrape() -> list[Grant]`; same API as other scrapers |

This document is implementation-ready and scoped only to the Reichman scholarships scraper.
