# Feature: Government Source – Miluim (IDF Reserve Student Grant)

## Goal

Provide a Government-based source for the IDF Reserve Student Grant
("סיוע חד פעמי בתשלום שכר הלימוד" / one-time tuition assistance for reservist students).

The source scrapes the official Miluim article page to extract grant amounts for:
- **מערך לוחם** (fighter units) – 100% tier
- **מערך עורפי** (rear units) – 30% tier

Users can see who is eligible, the two grant tiers with current amounts, and a link to the official site for full details.

---

## Product Vision

Users should be able to:

- See that there is a grant for reservist students
- Understand who is eligible (60+ days שמ״פ in צו 8)
- See the two grant types (לוחם / עורפי) with scraped amounts
- Click through to the official Miluim article for full details

---

## Architecture

- **Location:** `services/scraper/sources/government/miluim_student_grant.py`
- **Class:** `MiluimStudentGrantSource` (subclasses `SourceScraper`)
- **source_name:** `"government_miluim"`
- **base_url:** `https://www.miluim.idf.il`

### Implementation

- **Playwright** (sync API, headless) loads the article page.
- Wait for **networkidle** before capturing the DOM.
- **BeautifulSoup** parses the final HTML (no raw HTTP; content comes from Playwright).
- Extraction: find a paragraph containing `"סיוע חד פעמי בתשלום שכר הלימוד"`, then extract amounts with regex `r"\(([\d,\.]+)₪\)"` (first = fighter, second = rear). Numbers are normalized (commas removed).
- Browser is closed in a `finally` block after use.

### Target URL

`https://www.miluim.idf.il/articles-list/סטודנטים-ממילואים-ללימודים`

---

## Grant Model Mapping

The scraper returns **two** `Grant` objects.

### Shared fields (both grants)

- **source_name:** `"government_miluim"`
- **source_url:** The article URL above
- **eligibility:** `"סטודנטים שביצעו לפחות 60 ימי שמ״פ במסגרת צו 8 במהלך שירות מילואים פעיל."`
- **description:** `"סיוע חד פעמי בתשלום שכר לימוד עבור סטודנטים המשרתים במילואים במסגרת חרבות ברזל. היקף הסיוע תלוי בסוג היחידה (לוחם או עורפי)."`
- **deadline:** `None` (unless explicitly found on the page)
- **content_hash:** Computed via `content_hash` utility (per grant, so each has a distinct hash)
- **fetched_at:** `utc_now()`

### Grant 1 – מערך לוחם

- **title:** `"מענק מילואים לסטודנטים – מערך לוחם"`
- **amount:** Fighter amount (from page, normalized)
- **currency:** `"ILS"`

### Grant 2 – מערך עורפי

- **title:** `"מענק מילואים לסטודנטים – מערך עורפי"`
- **amount:** Rear amount (from page, normalized)
- **currency:** `"ILS"`

---

## Future Extension

Additional government benefits (e.g. "ממדים ללימודים" or other military-related grants) should live under `sources/government/`, each in its own file or as additional Grant entries.

---

## Expected Behavior

Calling:

    MiluimStudentGrantSource().scrape()

returns:

    list[Grant] with exactly two grants (מערך לוחם, מערך עורפי).

If the target paragraph or both amounts cannot be extracted, the method returns an empty list and logs a warning.
