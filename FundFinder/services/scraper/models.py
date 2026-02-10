from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Grant(BaseModel):

    title: str = Field(..., min_length=1, description="Original title (Hebrew/English)")
    description: str | None = Field(default=None,description="Full or summary; preserve original meaning",
    )
    source_url: str = Field(..., min_length=1, description="Canonical URL of the grant page")
    source_name: str = Field(...,min_length=1, description="Identifier of the scraper/site (e.g. mof_gov)",
    )
    deadline: date | None = Field(
        default=None,
        description="Normalized date; None if unclear",
    )
    deadline_text: str | None = Field(
        default=None,
        description="Raw deadline string (Hebrew months, until X, etc.)",
    )
    amount: str | None = Field(
        default=None,
        description="As displayed (e.g. ₪5,000, מלגה מלאה); no forced normalization",
    )
    currency: str | None = Field(
        default=None,
        description="Default ILS when clearly Israeli; None if unspecified",
    )
    eligibility: str | None = Field(
        default=None,
        description="Raw or lightly cleaned; Israeli terms kept",
    )
    content_hash: str = Field(
        ...,
        min_length=1,
        description="Stable hash for deduplication/change detection",
    )
    fetched_at: datetime = Field(
        ...,
        description="Scrape time (UTC)",
    )
    extra: dict[str, Any] | None = Field(
        default=None,
        description="Source-specific fields (e.g. application_link, contact_email)",
    )

    @field_validator("source_url")
    @classmethod
    def source_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_url must be non-empty")
        return v.strip()

    @field_validator("content_hash")
    @classmethod
    def content_hash_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content_hash must be non-empty")
        return v.strip()
