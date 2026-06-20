from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from kws_testset.models.audio import utc_now


class TransformJob(SQLModel, table=True):
    id: str = Field(primary_key=True)
    transform_kind: str = Field(index=True)
    status: str = Field(default="created", index=True)
    input_variant_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    processing_params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    requested_count: int = 0
    created_count: int = 0
    failed_count: int = 0
    created_variant_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    results: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
