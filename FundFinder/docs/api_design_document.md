# FundFinder REST API Design (MVP)

## 1. Overview

FundFinder aggregates scholarships from multiple sources. This document defines the **MVP REST API** that powers the frontend: list scholarships, paginate, search by keyword, filter, sort, and open a details page for a single scholarship.

**Scope:** Three endpoints only. Implementation should be straightforward using the existing PostgreSQL `grants` table and repository layer.

**Base URL:** `/api` (e.g. when served from the same origin as the frontend).

**Format:** All responses are JSON (`Content-Type: application/json`).

---

## 2. Data Model (grants)

The API exposes the existing **grants** table. Each grant has:

| Field           | Type        | Description |
|-----------------|-------------|-------------|
| `id`            | integer     | Primary key. |
| `title`         | string      | Grant title. |
| `description`   | string \| null | Description. |
| `source_url`    | string      | Canonical URL. |
| `source_name`   | string      | Source identifier (e.g. reichman, mod, huji). |
| `deadline`      | date \| null | Normalized deadline; null if unclear. |
| `deadline_text` | string \| null | Raw deadline text. |
| `amount`        | string \| null | Amount as displayed. |
| `currency`      | string \| null | Currency code (e.g. ILS, USD). |
| `eligibility`   | string \| null | Eligibility criteria. |
| `fetched_at`    | datetime (ISO 8601) | Last scrape time. |
| `extra`         | object \| null | Source-specific JSON. |
| `created_at`    | datetime (ISO 8601) | Created at. |
| `updated_at`    | datetime (ISO 8601) | Updated at. |

`content_hash` is not returned in API responses.

---

## 3. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/grants` | List grants (paginated, searchable, filterable, sortable). |
| `GET`  | `/api/grants/{id}` | Get a single grant by ID. |
| `GET`  | `/api/grants/filters` | Get filter options (source names, currencies). |

---

## 4. Request Parameters

### GET /api/grants

| Parameter     | Type    | Required | Default     | Description |
|---------------|---------|----------|-------------|-------------|
| `page`        | integer | No       | 1           | Page number (1-based). |
| `limit`       | integer | No       | 20          | Items per page. Max: 50. |
| `q`           | string  | No       | —           | Keyword search (title, description, eligibility). |
| `source_name` | string  | No       | —           | Filter by source name. May be repeated; backend applies `source_name IN (...)` (e.g. `?source_name=reichman&source_name=huji`). |
| `has_deadline`| boolean | No       | —           | If `true`, only grants with a deadline; if `false`, only without. |
| `sort_by`     | string  | No       | `deadline`  | Sort field (see Sorting). |
| `order`       | string  | No       | `asc`       | `asc` or `desc`. Invalid value → 400. |

**Validation:** `page` ≥ 1, `limit` 1–50. `order` must be `asc` or `desc`. Invalid `sort_by` or `order` → `400 Bad Request`.

### GET /api/grants/{id}

- **Path:** `id` — grant primary key (integer).
- **404** if not found.

### GET /api/grants/filters

- No query parameters for MVP. The backend returns **distinct** values: `SELECT DISTINCT source_name` and `SELECT DISTINCT currency` from the grants table, so no duplicates appear in the response.

---

## 5. Response Schemas

### Grant list item (GET /api/grants)

Each element in the `items` array uses this shape. The full `description` is **not** returned in the list; use `description_snippet` for previews (~200 characters, truncated). This keeps list payloads small.

```json
{
  "id": 1,
  "title": "מלגת מצוינות",
  "description_snippet": "מלגה לסטודנטים מצטיינים...",
  "source_url": "https://example.org/grant/1",
  "source_name": "reichman",
  "deadline": "2025-06-30",
  "deadline_text": "30 ביוני 2025",
  "amount": "₪10,000",
  "currency": "ILS",
  "eligibility": "סטודנטים שנה ב' ומעלה",
  "fetched_at": "2025-03-01T12:00:00Z",
  "extra": null,
  "created_at": "2025-01-15T08:00:00Z",
  "updated_at": "2025-03-01T12:00:00Z"
}
```

### Grant object (full) — GET /api/grants/{id}

Single-grant response includes the full `description` (no snippet). Dates/datetimes in ISO 8601.

```json
{
  "id": 1,
  "title": "מלגת מצוינות",
  "description": "מלגה לסטודנטים מצטיינים...",
  "source_url": "https://example.org/grant/1",
  "source_name": "reichman",
  "deadline": "2025-06-30",
  "deadline_text": "30 ביוני 2025",
  "amount": "₪10,000",
  "currency": "ILS",
  "eligibility": "סטודנטים שנה ב' ומעלה",
  "fetched_at": "2025-03-01T12:00:00Z",
  "extra": null,
  "created_at": "2025-01-15T08:00:00Z",
  "updated_at": "2025-03-01T12:00:00Z"
}
```

### List response (GET /api/grants)

```json
{
  "items": [ { /* Grant list item (description_snippet) */ }, ... ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### Single grant (GET /api/grants/{id})

Returns one full Grant object (with `description`, not `description_snippet`).

### Filter options (GET /api/grants/filters)

```json
{
  "source_names": ["reichman", "mod", "huji", "government"],
  "currencies": ["ILS", "USD"]
}
```

Values are **distinct** (no duplicates). Omit null currencies or include a sentinel (e.g. `"unspecified"`) as needed for the frontend.

### Error response

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Grant with id 999 not found."
  }
}
```

Use `400` for bad parameters, `404` for missing grant, `422` for validation (e.g. page/limit out of range), `500` for server errors.

---

## 6. Pagination

- **Style:** Page-based. Query: `?page=1&limit=20`.
- **Defaults:** `page=1`, `limit=20`; cap `limit` at **50**.
- **Response:** Include `items` (array of grants) and `pagination` with:
  - `page`, `limit`
  - `total_items` (count matching filters/search)
  - `total_pages` = ceil(total_items / limit)
  - `has_next`, `has_prev` (booleans)

Run the same filters/search for the count query so pagination reflects the current result set.

---

## 7. Filtering

- **`q` (keyword search):** Apply to `title`, `description`, and `eligibility`. MVP implementation: SQL `ILIKE %q%` on each field (OR). Empty `q` is ignored.
- **`source_name`:** May be sent multiple times (e.g. `?source_name=reichman&source_name=huji`). Backend interprets as **`source_name IN (...)`** — return grants whose `source_name` is any of the given values.
- **`has_deadline`:**  
  - `true` → `deadline IS NOT NULL`  
  - `false` → `deadline IS NULL`

All filters are combined with AND.

---

## 8. Sorting

- **Parameters:** `sort_by`, `order`.
- **Default:** `sort_by=deadline`, `order=asc`, with **`NULLS LAST`** for the sort column (so grants with the closest deadlines appear first; grants with no deadline appear at the end).
- **Allowed `sort_by` values:** `deadline`, `created_at`, `updated_at`, `title`. Invalid value → 400.
- **`order`:** Must be one of `asc` or `desc`. Invalid value → 400 Bad Request.
- **Security:** Validate `sort_by` and `order` against the whitelist; do not pass user input directly into `ORDER BY`.

---

## 9. Future AI Search

The product may later add **LLM-powered natural language search**. For example:

- **Endpoint:** `POST /api/search` (or similar).
- **Behavior:** Accept a natural language query and return grants ranked by relevance, with the same pagination shape (`items` + `pagination`).

No further design or implementation is required for the MVP. When adding it, keep `GET /api/grants` for keyword search and filters; the new endpoint can sit alongside it and reuse the same Grant schema and pagination format.

---

## Summary

| Endpoint | Purpose |
|----------|---------|
| `GET /api/grants` | List with pagination (max 50 per page), keyword search (`q`), filters (`source_name` repeatable → IN, `has_deadline`), and sort (default: deadline asc, NULLS LAST). Returns `description_snippet`, not full `description`. |
| `GET /api/grants/{id}` | Full details for one grant (includes full `description`). |
| `GET /api/grants/filters` | Distinct source names and currencies for dropdowns (no duplicates). |

This is enough for a backend engineer to implement the MVP API on top of the existing database and repository.
