"""Run all scrapers and persist grants to PostgreSQL.

Run from FundFinder project root with the project env activated, e.g.:
  cd FundFinder
  source .venv/bin/activate
  python scripts/run_pipeline_and_persist.py

Prerequisites:
  - PostgreSQL running locally (brew services start postgresql)
  - Database created: createdb fundfinder
  - Tables created (run once): python -m backend.db.schema

Environment:
  - DATABASE_URL (optional): defaults to postgresql://localhost:5432/fundfinder
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if _root not in sys.path:
    sys.path.insert(0, str(_root))

from backend.db import GrantRepository, create_tables, get_connection
from services.scraper.pipeline import get_all_scrapers, run_sources

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Running pipeline (all scrapers)...")
    grants = run_sources(get_all_scrapers())
    logger.info("Pipeline returned %d grants", len(grants))

    if not grants:
        logger.info("No grants to persist")
        return

    with get_connection() as conn:
        create_tables(conn)
        repo = GrantRepository()
        count = repo.upsert_many(conn, grants)
        conn.commit()

    logger.info("Persisted %d grants", count)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
