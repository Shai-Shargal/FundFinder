"""Database schema for FundFinder. Creates grants table and indexes."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for scripts run via python -m
_root = Path(__file__).resolve().parent.parent.parent
if _root not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Any

from backend.db.connection import get_connection

DDL = """
CREATE TABLE IF NOT EXISTS grants (
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

CREATE INDEX IF NOT EXISTS idx_grants_source_name ON grants(source_name);
CREATE INDEX IF NOT EXISTS idx_grants_deadline ON grants(deadline);
CREATE INDEX IF NOT EXISTS idx_grants_fetched_at ON grants(fetched_at);
CREATE INDEX IF NOT EXISTS idx_grants_content_hash ON grants(content_hash);
"""


def create_tables(conn: Any) -> None:
    """Create grants table and indexes. Idempotent (IF NOT EXISTS)."""
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def drop_tables(conn: Any) -> None:
    """Drop grants table. For tests or reset."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS grants CASCADE")
    conn.commit()


if __name__ == "__main__":
    with get_connection() as conn:
        create_tables(conn)
    print("Schema created successfully.")
