from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from kws_testset.models.audio import utc_now


class ImportBatch(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    source_directory: str | None = None
    file_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    status: str = "draft"
    default_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
