"""Database connection for FundFinder backend."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2

DEFAULT_DATABASE_URL = "postgresql://localhost:5432/fundfinder"


def get_database_url() -> str:
    """Return DATABASE_URL from environment or default."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager yielding a psycopg2 connection. Closes on exit."""
    conn = psycopg2.connect(get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
