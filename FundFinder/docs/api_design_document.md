# FundFinder REST API Design Document

## 1. Overview

This document describes the REST API for **FundFinder**, a platform that aggregates scholarships from multiple sources. The API powers a frontend that lists, searches, filters, and displays scholarship (grant) details.

**Design goals:**

- **RESTful**: Resource-oriented URLs, standard HTTP methods, clear status codes.
- **Consistent**: Uniform request/response shapes, pagination, and error format.
- **Extensible**: Filter and sort parameters are designed so new ones can be added; a future semantic (LLM) search endpoint is anticipated.

**Base URL (example):** `https://api.fundfinder.example.com` or `/api` when served from the same origin.

**Data model:** The API exposes **grants** (scholarships). Each grant is stored in PostgreSQL with the following logical fields (aligned with the existing `grants` table):

| Field          | Type        | Description |
|----------------|-------------|-------------|
| `id`           | integer     | Primary key (BIGSERIAL). |
| `title`        | string      | Grant title. |
| `description`  | string \| null | Full or summary description. |
| `source_url`   | string      | Canonical URL of the grant page. |
| `source_name`  | string      | Identifier of the source (e.g. reichman, mod, huji). |
| `deadline`     | date \| null | Normalized deadline date; `null` if unclear. |
| `deadline_text`| string \| null | Raw deadline string (e.g. "עד סוף מרץ"). |
| `amount`       | string \| null | Amount as displayed (e.g. "₪5,000", "מלגה מלאה"). |
| `currency`     | string \| null | Currency code (e.g. ILS, USD). |
| `eligibility`  | string \| null | Eligibility criteria (raw or lightly cleaned). |
| `content_hash` | string      | Hash for deduplication (optional in responses). |
| `fetched_at`   | datetime (ISO 8601) | When the record was last scraped. |
| `extra`        | object \| null | Source-specific JSON (e.g. application_link, contact_email). |
| `created_at`   | datetime (ISO 8601) | Record creation time. |
| `updated_at`   | datetime (ISO 8601) | Last update time. |

---

## 2. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/grants` | List grants with pagination, search, filters, and sorting. |
| `GET`  | `/api/grants/:id` | Get a single grant by ID. |
| `GET`  | `/api/grants/filters` | Get available filter options (source names, currencies). |
| `POST` | `/api/grants/semantic-search` | *(Future)* Natural-language search (LLM-based). |

All responses use **JSON**. Use `Content-Type: application/json` and `Accept: application/json` where applicable.

---

## 3. Request Parameters

### 3.1 `GET /api/grants`

| Parameter       | Type   | Required | Default | Description |
|----------------|--------|----------|---------|-------------|
| `page`         | integer| No       | 1       | Page number (1-based). |
| `limit`        | integer| No       | 20      | Items per page. Max: 100. |
| `q`            | string | No       | —       | Full-text search query (searches title, description, eligibility). |
| `source_name`  | string | No       | —       | Filter by exact source name. Can be repeated for multiple (e.g. `source_name=reichman&source_name=mod`). |
| `has_deadline` | boolean| No       | —       | If `true`, only grants with non-null `deadline`. If `false`, only grants with null `deadline`. |
| `deadline_before` | date (YYYY-MM-DD) | No | —   | Only grants with `deadline <= deadline_before`. |
| `currency`     | string | No       | —       | Filter by currency (e.g. ILS, USD). Can be repeated. |
| `sort_by`      | string | No       | `updated_at` | Field to sort by. Allowed: `id`, `title`, `deadline`, `updated_at`, `created_at`, `source_name`, `amount`. |
| `order`        | string | No       | `desc`  | Sort order: `asc` or `desc`. |

**Validation:**

- `page` ≥ 1, `limit` between 1 and 100.
- `sort_by` must be one of the allowed values; otherwise return `400 Bad Request`.
- `order` must be `asc` or `desc`.
- Invalid `deadline_before` format → `400 Bad Request`.

### 3.2 `GET /api/grants/:id`

- **Path parameter:** `id` — grant primary key (integer).
- **Behavior:** If the grant does not exist, return `404 Not Found`.

### 3.3 `GET /api/grants/filters`

Optional query parameters to scope which grants are considered for options:

| Parameter       | Type   | Required | Description |
|----------------|--------|----------|-------------|
| `source_name`  | string | No       | If provided, only return filter options for grants matching this source (e.g. for a “refine by currency” UI). |
| `currency`     | string | No       | If provided, only return options for grants with this currency. |

If no query params are given, return all distinct source names and all distinct currencies across the entire table.

### 3.4 `POST /api/grants/semantic-search` (Future)

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `query`   | string | Yes      | Natural language search query (e.g. "scholarships for students who served in the military"). |
| `page`    | integer| No       | 1-based page. Default: 1. |
| `limit`   | integer| No       | Items per page. Default: 20, max: 100. |

Request body (JSON): `{ "query": "...", "page": 1, "limit": 20 }`.

---

## 4. Response Schemas

### 4.1 Grant object (single grant)

Returned in `GET /api/grants/:id` and inside the `items` array of `GET /api/grants`. Dates and datetimes in ISO 8601.

```json
{
  "id": 1,
  "title": "מלגת מצוינות",
  "description": "מלגה לסטודנטים מצטיינים...",
  "source_url": "https://example.org/grant/1",
  "source_name": "reichman",
  "deadline": "2025-06-30",
  "deadline_text": "עד 30 ביוני 2025",
  "amount": "₪10,000",
  "currency": "ILS",
  "eligibility": "סטודנטים שנה ב' ומעלה",
  "fetched_at": "2025-03-01T12:00:00Z",
  "extra": { "application_link": "https://..." },
  "created_at": "2025-01-15T08:00:00Z",
  "updated_at": "2025-03-01T12:00:00Z"
}
```

- `content_hash` may be omitted in API responses to keep payloads smaller; include only if needed for sync/change detection.

### 4.2 List response: `GET /api/grants`

Paginated list with metadata.

```json
{
  "items": [ { /* Grant object */ }, ... ],
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

- `total_items`: total count matching the current filters/search (before pagination).
- `total_pages`: `ceil(total_items / limit)`.
- `has_next`: `page < total_pages`.
- `has_prev`: `page > 1`.

### 4.3 Filter options response: `GET /api/grants/filters`

```json
{
  "source_names": ["reichman", "mod", "huji", "government"],
  "currencies": ["ILS", "USD", null]
}
```

- `null` in `currencies` represents grants with no currency set. Frontend can display it as “Unspecified” or “Any”.

### 4.4 Future semantic search response: `POST /api/grants/semantic-search`

Same shape as list response, with optional relevance score:

```json
{
  "items": [
    {
      "grant": { /* Grant object */ },
      "score": 0.92
    }
  ],
  "pagination": { /* same as 4.2 */ }
}
```

### 4.5 Error response

All errors use a consistent JSON body:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Grant with id 999 not found."
  }
}
```

**HTTP status codes:**

- `200 OK` — Success (list, single grant, filters).
- `400 Bad Request` — Invalid parameters (e.g. invalid `sort_by`, `order`, or date format).
- `404 Not Found` — Grant not found for `GET /api/grants/:id`.
- `422 Unprocessable Entity` — Validation errors (e.g. `page` or `limit` out of range).
- `500 Internal Server Error` — Server error.

---

## 5. Pagination Strategy

- **Style:** Page-based, 1-based page index.
- **Parameters:** `page` (default 1), `limit` (default 20, max 100).
- **Count:** For `GET /api/grants`, run a `COUNT(*)` (or equivalent) with the same filters and search as the main query so `total_items` and `total_pages` reflect the filtered result set.
- **Performance:** For large tables, consider a capped count (e.g. stop counting after 10,000) or caching counts per filter combination to avoid expensive full scans. Document this if adopted.
- **Headers (optional):** You may add `X-Total-Count`, `X-Page`, `X-Per-Page` for clients that prefer header-based pagination.

---

## 6. Filtering Strategy

- **Text search (`q`):** Apply to `title`, `description`, and `eligibility`. Use database full-text search (e.g. PostgreSQL `to_tsvector` / `to_tsquery` or `ilike`/`%q%`) for consistent behavior. Empty `q` is ignored.
- **source_name:** Exact match on `source_name`. Multiple values: OR (e.g. `source_name=reichman&source_name=mod` → grants from reichman OR mod).
- **has_deadline:**  
  - `true` → `deadline IS NOT NULL`  
  - `false` → `deadline IS NULL`
- **deadline_before:** `deadline IS NOT NULL AND deadline <= :deadline_before`.
- **currency:** Exact match on `currency`. Multiple values: OR. For “grants with no currency”, the frontend can send a special value (e.g. `currency=__none__`) that the backend maps to `currency IS NULL`.

Filters are combined with **AND** (e.g. source_name=reichman AND has_deadline=true AND deadline_before=2025-12-31).

---

## 7. Sorting Strategy

- **Parameters:** `sort_by` (field name), `order` (`asc` | `desc`).
- **Default:** `sort_by=updated_at`, `order=desc` (newest first).
- **Allowed `sort_by` values:** `id`, `title`, `deadline`, `updated_at`, `created_at`, `source_name`, `amount`.
- **Nulls:** For `deadline`, define a consistent nulls order (e.g. `NULLS LAST` for `asc`, `NULLS FIRST` for `desc`) and document it.
- **Security:** Validate `sort_by` against a whitelist to avoid SQL injection; do not pass user input directly into `ORDER BY`.

---

## 8. Future LLM Integration

**Endpoint:** `POST /api/grants/semantic-search`

**Purpose:** Allow natural language queries (e.g. “scholarships for students who served in the military”) and return grants ranked by semantic relevance.

**Integration approach:**

1. **Embedding-based search**
   - Precompute embeddings for each grant (e.g. from `title + description + eligibility`) and store in a vector column (e.g. PostgreSQL `pgvector`) or in a vector store.
   - At request time: call an embedding API to get the query vector, then run a similarity search (e.g. cosine similarity) and return grant IDs with scores.
   - Paginate over the top-K results (e.g. skip/limit by `page` and `limit`).

2. **LLM rerank (optional)**
   - Optionally use an LLM to rerank a candidate set (e.g. top 50 from vector search) for better relevance before applying pagination.

3. **API contract**
   - Request: `{ "query": "natural language string", "page": 1, "limit": 20 }`.
   - Response: Same paginated structure as list, with each item containing `grant` and `score` (relevance score 0–1).
   - Reuse the same Grant JSON schema and pagination metadata.

4. **Backward compatibility**
   - Keep `GET /api/grants` for keyword filters and full-text `q`; semantic search is an additional path. Frontend can offer both “Keyword search” and “Natural language search” and call the appropriate endpoint.

5. **Implementation notes**
   - Add a migration for an `embedding` column (or separate table) when ready.
   - Run an embedding job after scrape/pipeline updates so new/updated grants are searchable.
   - Consider rate limiting and caching for the embedding endpoint due to external API usage.

---

## 9. Example Requests and Responses

### 9.1 List grants (first page, default sort)

**Request:**

```http
GET /api/grants?page=1&limit=20
Accept: application/json
```

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": 42,
      "title": "מלגת מצוינות",
      "description": "מלגה לסטודנטים מצטיינים בשנה ב' ומעלה.",
      "source_url": "https://example.org/grant/42",
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
  ],
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

---

### 9.2 List with search and filters

**Request:**

```http
GET /api/grants?q=מצוינות&source_name=reichman&has_deadline=true&deadline_before=2025-12-31&currency=ILS&sort_by=deadline&order=asc&page=1&limit=10
Accept: application/json
```

**Response:** `200 OK` — Same structure as 9.1, with `items` and `pagination` reflecting the filtered and sorted result.

---

### 9.3 Get single grant

**Request:**

```http
GET /api/grants/42
Accept: application/json
```

**Response:** `200 OK`

```json
{
  "id": 42,
  "title": "מלגת מצוינות",
  "description": "מלגה לסטודנטים מצטיינים בשנה ב' ומעלה.",
  "source_url": "https://example.org/grant/42",
  "source_name": "reichman",
  "deadline": "2025-06-30",
  "deadline_text": "30 ביוני 2025",
  "amount": "₪10,000",
  "currency": "ILS",
  "eligibility": "סטודנטים שנה ב' ומעלה",
  "fetched_at": "2025-03-01T12:00:00Z",
  "extra": { "application_link": "https://apply.example.org/42" },
  "created_at": "2025-01-15T08:00:00Z",
  "updated_at": "2025-03-01T12:00:00Z"
}
```

**Response:** `404 Not Found`

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Grant with id 999 not found."
  }
}
```

---

### 9.4 Get filter options

**Request:**

```http
GET /api/grants/filters
Accept: application/json
```

**Response:** `200 OK`

```json
{
  "source_names": ["reichman", "mod", "huji", "government"],
  "currencies": ["ILS", "USD", null]
}
```

---

### 9.5 Invalid parameters

**Request:**

```http
GET /api/grants?sort_by=invalid_field&order=invalid
Accept: application/json
```

**Response:** `400 Bad Request`

```json
{
  "error": {
    "code": "INVALID_PARAMS",
    "message": "Invalid sort_by: allowed values are id, title, deadline, updated_at, created_at, source_name, amount."
  }
}
```

---

### 9.6 Future: Semantic search

**Request:**

```http
POST /api/grants/semantic-search
Content-Type: application/json
Accept: application/json

{
  "query": "scholarships for students who served in the military",
  "page": 1,
  "limit": 20
}
```

**Response:** `200 OK` (when implemented)

```json
{
  "items": [
    {
      "grant": {
        "id": 7,
        "title": "מלגת חיילים משוחררים",
        "description": "...",
        "source_url": "https://...",
        "source_name": "mod",
        "deadline": "2025-08-01",
        "deadline_text": null,
        "amount": "₪15,000",
        "currency": "ILS",
        "eligibility": "חיילים משוחררים בשנים האחרונות",
        "fetched_at": "2025-03-01T12:00:00Z",
        "extra": null,
        "created_at": "2025-01-10T08:00:00Z",
        "updated_at": "2025-03-01T12:00:00Z"
      },
      "score": 0.92
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 5,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

## Summary

This design provides:

- **Listing** with pagination (`page`, `limit`), full-text search (`q`), and filters (`source_name`, `has_deadline`, `deadline_before`, `currency`).
- **Single grant** by `id` via `GET /api/grants/:id`.
- **Filter options** via `GET /api/grants/filters` for source names and currencies.
- **Consistent** response shapes (Grant object, paginated list, error body) and clear validation rules.
- **Future-ready** `POST /api/grants/semantic-search` with a defined contract and integration approach (embeddings + optional rerank).

An engineer can implement the API from this document by adding an API layer (e.g. FastAPI or Flask) that uses the existing repository for DB access and extends it with the new query parameters, count query, and filter-options query.
