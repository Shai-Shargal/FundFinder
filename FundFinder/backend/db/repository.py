"""Grant repository: upsert and query grants."""

from __future__ import annotations

import json

from services.scraper.models import Grant


def _row_to_grant(row: tuple) -> Grant:
    """Map a DB row to a Grant model."""
    (
        id_,
        title,
        description,
        source_url,
        source_name,
        deadline,
        deadline_text,
        amount,
        currency,
        eligibility,
        content_hash,
        fetched_at,
        extra,
        created_at,
        updated_at,
    ) = row
    extra_dict: dict | None = None
    if extra is not None:
        if isinstance(extra, dict):
            extra_dict = extra
        else:
            extra_dict = json.loads(extra) if extra else None
    return Grant(
        title=title,
        description=description,
        source_url=source_url,
        source_name=source_name,
        deadline=deadline,
        deadline_text=deadline_text,
        amount=amount,
        currency=currency,
        eligibility=eligibility,
        content_hash=content_hash,
        fetched_at=fetched_at,
        extra=extra_dict,
    )


UPSERT_SQL = """
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
    updated_at = NOW()
"""


class GrantRepository:
    """Repository for persisting and querying grants."""

    def upsert_many(self, conn, grants: list[Grant]) -> int:
        """Upsert grants by source_url. Returns number of grants processed."""
        if not grants:
            return 0
        cur = conn.cursor()
        try:
            for g in grants:
                extra_json = json.dumps(g.extra, ensure_ascii=False) if g.extra else None
                cur.execute(
                    UPSERT_SQL,
                    (
                        g.title,
                        g.description,
                        g.source_url,
                        g.source_name,
                        g.deadline,
                        g.deadline_text,
                        g.amount,
                        g.currency,
                        g.eligibility,
                        g.content_hash,
                        g.fetched_at,
                        extra_json,
                    ),
                )
            conn.commit()
            return len(grants)
        finally:
            cur.close()

    def get_all(self, conn) -> list[Grant]:
        """Fetch all grants as Grant models."""
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, title, description, source_url, source_name, deadline, "
                "deadline_text, amount, currency, eligibility, content_hash, fetched_at, "
                "extra, created_at, updated_at FROM grants ORDER BY id"
            )
            return [_row_to_grant(row) for row in cur.fetchall()]
        finally:
            cur.close()

    def get_by_source(self, conn, source_name: str) -> list[Grant]:
        """Fetch grants filtered by source_name."""
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, title, description, source_url, source_name, deadline, "
                "deadline_text, amount, currency, eligibility, content_hash, fetched_at, "
                "extra, created_at, updated_at FROM grants WHERE source_name = %s ORDER BY id",
                (source_name,),
            )
            return [_row_to_grant(row) for row in cur.fetchall()]
        finally:
            cur.close()
