from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from kws_testset.models.audio import utc_now


class DatasetSpec(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    target_keyword: str
    target_keyword_normalized: str
    sampling_seed: int = 20260617
    status: str = "active"
    quotas: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    filters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    balance_by: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    min_duration_sec: float | None = None
    max_duration_sec: float | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ManualOverride(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_spec_id: str = Field(index=True)
    variant_id: str = Field(index=True)
    action: str
    reason: str
    created_at: datetime = Field(default_factory=utc_now)


class DatasetVersion(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_spec_id: str = Field(index=True)
    version: int
    name: str
    build_status: str = "built"
    sampling_seed: int
    rules_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    coverage_summary: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    item_count: int = 0
    total_duration_sec: float = 0.0
    export_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    built_at: datetime | None = None
    exported_at: datetime | None = None


class DatasetItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_version_id: str = Field(index=True)
    variant_id: str = Field(index=True)
    sample_type: str = Field(index=True)
    text: str
    normalized_text: str
    duration_sec: float
    selection_reason: str
    selection_rank: int
    metadata_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
