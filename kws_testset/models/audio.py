from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioSource(SQLModel, table=True):
    id: str = Field(primary_key=True)
    original_filename: str
    stored_path: str
    sha256: str = Field(index=True, unique=True)
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int | None = None
    import_batch_id: str | None = Field(default=None, index=True)
    imported_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class AudioVariant(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source_id: str = Field(index=True)
    parent_variant_id: str | None = Field(default=None, index=True)
    variant_kind: str = Field(default="original", index=True)
    stored_path: str
    sha256: str = Field(index=True, unique=True)
    duration_sec: float
    sample_rate: int
    channels: int
    text: str = ""
    normalized_text: str = ""
    sample_type: str = "ordinary_negative"
    quality_status: str = Field(default="draft", index=True)
    voice_source: str = "unknown"
    speaker_id: str | None = None
    gender: str = "unknown"
    age_group: str = "unknown"
    timbre_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    volume: str = "unknown"
    pitch: str = "unknown"
    speed: str = "unknown"
    noise_scene: str = "unknown"
    snr_bucket: str | None = None
    impairment_type: str = "none"
    impairment_chain: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    processing_params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    custom_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
