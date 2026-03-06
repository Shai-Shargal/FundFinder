# FundFinder — Database Implementation Design

## 1. Overview

This document describes the design for adding persistent storage to FundFinder. Grants produced by scrapers will be stored in a PostgreSQL database, enabling querying, change detection, and future API exposure.

**Goals:**

- Persist all scraped grants in a PostgreSQL database
- Support deduplication and change detection via `content_hash`
- Keep `services/scraper/` unchanged; add a new `backend/db/` layer
- Use local PostgreSQL for development; support cloud PostgreSQL for production via env config

---

## 2. Architecture

We follow **Option B** layout: backend and frontend at top level; `services/` remains shared domain logic.

```
FundFinder/
├── backend/
│   ├── db/                    # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py      # Connection pool, session factory
│   │   ├── schema.py          # Table definitions (SQL or SQLAlchemy)
│   │   └── repository.py      # GrantRepository: upsert, query
│   └── api/                   # (Future) HTTP API
│
├── services/
│   └── scraper/               # Unchanged
│       ├── sources/
│       ├── pipeline.py
│       └── models.py          # Grant Pydantic model
│
├── scripts/                   # Scripts that run pipeline + persist
└── docs/
```

**Data flow:**

1. `services.scraper.pipeline.run_sources()` returns `list[Grant]`
2. A script or future job calls `GrantRepository.upsert_many(grants)`
3. `backend.db` persists grants and upserts by `source_url` (one row per grant page; updates when content changes)

---

## 3. Technology Choices

| Choice | Rationale |
|--------|-----------|
| **PostgreSQL** | Production-ready, supports JSONB for `extra`, good tooling |
| **Local PostgreSQL** | Installed via Homebrew; no cloud dependency during development |
| **psycopg2 or asyncpg** | Standard Python drivers; start with `psycopg2` (sync) for simplicity |
| **Raw SQL or SQLAlchemy** | Start with raw SQL + `psycopg2` for clarity; migrate to SQLAlchemy if ORM benefits emerge |

---

## 4. Schema Design

### 4.1 Grants Table

Maps 1:1 to the `Grant` Pydantic model in `services/scraper/models.py`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `SERIAL` / `BIGSERIAL` | No | Primary key, auto-increment |
| `title` | `TEXT` | No | Grant title (Hebrew/English) |
| `description` | `TEXT` | Yes | Full or summary description |
| `source_url` | `TEXT` | No | Canonical URL of the grant page |
| `source_name` | `VARCHAR(64)` | No | Scraper identifier (e.g. `reichman`, `huji`) |
| `deadline` | `DATE` | Yes | Normalized deadline date |
| `deadline_text` | `TEXT` | Yes | Raw deadline string |
| `amount` | `TEXT` | Yes | As displayed (e.g. ₪5,000) |
| `currency` | `VARCHAR(8)` | Yes | e.g. ILS |
| `eligibility` | `TEXT` | Yes | Raw or cleaned eligibility text |
| `content_hash` | `VARCHAR(64)` | No | SHA-256 hex for change detection (not used as unique key) |
| `fetched_at` | `TIMESTAMPTZ` | No | Scrape time (UTC) |
| `extra` | `JSONB` | Yes | Source-specific fields |
| `created_at` | `TIMESTAMPTZ` | No | First insert time |
| `updated_at` | `TIMESTAMPTZ` | No | Last update time |

**Indexes:**

- `UNIQUE(source_url)` — one row per grant page; enables upsert by URL (prevents duplicates when grant content changes)
- `INDEX(source_name)` — filter by source
- `INDEX(deadline)` — filter by deadline (for "upcoming" queries)
- `INDEX(content_hash)` — optional; for change-detection queries

### 4.2 SQL DDL (Reference)

```sql
CREATE TABLE grants (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    source_url TEXT NOT NULL UNIQUE,
    source_name VARCHAR(64) NOT NULL,
    deadline DATE,
    deadline_text TEXT,
    amount TEXT,
    currency VARCHAR(8),
    eligibility TEXT,
    content_hash VARCHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    extra JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_grants_source_name ON grants(source_name);
CREATE INDEX idx_grants_deadline ON grants(deadline);
CREATE INDEX idx_grants_fetched_at ON grants(fetched_at);
CREATE INDEX idx_grants_content_hash ON grants(content_hash);
```

---

## 5. Upsert Strategy

**Key:** `source_url` is the natural key. Same URL = same grant page. When a grant's content changes (description, deadline, amount, etc.), `content_hash` changes—but we update the existing row instead of creating a duplicate.

**Why not `content_hash`?** If we used `UNIQUE(content_hash)`, every content change would create a new row. The same grant would appear multiple times. Using `UNIQUE(source_url)` ensures one row per grant page; updates overwrite the existing row.

**Role of `content_hash`:** Used for change detection only (e.g. compare old vs new hash to know if a grant was updated, for notifications or changelog). Not used as the upsert key.

**Behavior:**

- **Insert** if `source_url` does not exist
- **Update** if `source_url` exists: refresh `title`, `description`, `deadline`, `amount`, `eligibility`, `content_hash`, `fetched_at`, `extra`; set `updated_at = NOW()`
- `created_at` is set on insert only and never changed

**PostgreSQL upsert:**

```sql
INSERT INTO grants (title, description, source_url, source_name, deadline, deadline_text,
                    amount, currency, eligibility, content_hash, fetched_at, extra,
                    created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
ON CONFLICT (source_url) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    deadline = EXCLUDED.deadline,
    deadline_text = EXCLUDED.deadline_text,
    amount = EXCLUDED.amount,
    currency = EXCLUDED.currency,
    eligibility = EXCLUDED.eligibility,
    content_hash = EXCLUDED.content_hash,
    fetched_at = EXCLUDED.fetched_at,
    extra = EXCLUDED.extra,
    updated_at = NOW();
```

---

## 6. Backend DB Module Structure

### 6.1 `backend/db/connection.py`

- Read `DATABASE_URL` from environment (default: `postgresql://localhost:5432/fundfinder`)
- Provide a connection factory or context manager
- Optional: connection pooling for future API use

### 6.2 `backend/db/schema.py`

- `create_tables(conn)` — run DDL to create `grants` table and indexes
- `drop_tables(conn)` — for tests or reset (optional)
- Idempotent where possible (e.g. `CREATE TABLE IF NOT EXISTS`)

### 6.3 `backend/db/repository.py`

- `GrantRepository` class
  - `upsert_many(conn, grants: list[Grant]) -> int` — upsert grants; return count of rows affected
  - `get_all(conn) -> list[Grant]` — fetch all grants as Pydantic models
  - `get_by_source(conn, source_name: str) -> list[Grant]`
  - `get_by_deadline_range(conn, from_date, to_date) -> list[Grant]` (optional, for later)

Conversion between DB rows and `Grant` is done here (or in a small `mapper` helper).

---

## 7. Pipeline Integration

**Option A: Script-based (recommended for Phase 1)**

A script (e.g. `scripts/run_pipeline_and_persist.py`) does:

1. `grants = run_sources(get_all_scrapers())`
2. `repo = GrantRepository()`
3. `with get_connection() as conn: repo.upsert_many(conn, grants)`

**Option B: Pipeline returns; caller persists**

`pipeline.run_sources()` stays pure (returns `list[Grant]`). Any script, cron job, or API endpoint that runs the pipeline is responsible for calling the repository. No changes to `services/scraper/`.

---

## 8. Environment & Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://localhost:5432/fundfinder` | PostgreSQL connection string |

**Local setup:**

1. Create database: `createdb fundfinder`
2. (Optional) Create user and set `DATABASE_URL` in `.env`
3. Run schema: `python -m backend.db.schema` or via a small CLI

**Production:** Set `DATABASE_URL` to cloud PostgreSQL (Supabase, Neon, RDS, etc.).

---

## 9. Migration Strategy

**Phase 1 (this implementation):** Manual DDL in `schema.py`. Run once to create tables.

**Phase 2 (optional):** Introduce migration tool (e.g. Alembic) when schema changes become frequent or multiple environments need coordinated migrations.

---

## 10. Implementation Phases

| Phase | Scope |
|-------|--------|
| **1. Structure** | Create `backend/db/` with `__init__.py`, `connection.py`, `schema.py`, `repository.py` |
| **2. Schema** | Implement `create_tables()` with grants table and indexes |
| **3. Repository** | Implement `GrantRepository.upsert_many()` and `get_all()` |
| **4. Script** | Add `scripts/run_pipeline_and_persist.py` to run pipeline and persist |
| **5. Tests** | Unit tests for repository (use temp DB or SQLite for speed, or local PostgreSQL) |

---

## 11. Dependencies

Add to `requirements.txt`:

```
psycopg2-binary>=2.9.0
```

Or `psycopg[binary]` if using the newer `psycopg` (v3) package.

---

## 12. References

- Grant model: `services/scraper/models.py`
- Pipeline: `services/scraper/pipeline.py`
- Design PoC: `docs/design-PoC.md`
