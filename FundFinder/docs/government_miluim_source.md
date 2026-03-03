# Feature: Government Source – Miluim (IDF Reserve Student Grant)

## Goal

Add a new Government-based source that represents the IDF Reserve Student Grant
("חרבות ברזל" / Student Reserve Grant).

This is NOT a dynamic scraper.

This source represents a policy-level grant that:
- Applies nationwide
- Is not institution-specific
- Changes infrequently
- Does not require scraping HTML

The goal is to normalize and expose high-level grant information
in a clean and minimal way.

---

## Product Vision

Users should be able to:

- Enter the site
- See that there is a grant for reservists
- Understand:
  - Who is eligible
  - For which academic year
  - Whether the amount is fixed or variable
- Click a link to the official government site for full details

We are NOT reproducing the full page.
We are NOT scraping dynamic content.
We are providing structured access to public information.

---

## Architecture Decision

This source will:

- Live under:

    services/scraper/sources/government/miluim.py

- Subclass `SourceScraper`
- Return a static `Grant` object
- Not perform HTTP requests
- Not use BeautifulSoup
- Not depend on external HTML

Reason:
This is a policy-based benefit, not a dynamic scholarship list.

---

## Grant Model Mapping

The Miluim grant should be normalized into a single Grant object.

### Fields:

- title:
  "מענק מילואים לסטודנטים – חרבות ברזל"

- source_name:
  "government_miluim"

- source_url:
  Official IDF Miluim site URL

- deadline:
  None (unless official closing date is clearly defined)

- amount:
  None (amount varies depending on days served)

- currency:
  None

- eligibility:
  Short structured summary, e.g.:
  "משרתי מילואים פעילים שהם סטודנטים בשנת הלימודים הרלוונטית"

- description:
  High-level explanation:
  "מענק משתנה בהתאם למספר ימי השירות במסגרת חרבות ברזל..."

---

## What We Explicitly Do NOT Do

- Do not scrape HTML
- Do not parse numeric values from examples
- Do not try to compute grant amounts
- Do not embed large policy text blocks
- Do not depend on frontend DOM structure

---

## Future Extension

If later we want to:

- Add more government benefits
- Add “ממדים ללימודים”
- Add additional military-related grants

They should live under:

    sources/government/

Each as a separate file or as separate Grant entries.

---

## Expected Behavior

Calling:

    MiluimSource().scrape()

Should return:

    list[Grant] with exactly one normalized grant.