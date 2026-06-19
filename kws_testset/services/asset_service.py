from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioVariant
from kws_testset.services.text_normalize import normalize_text
from kws_testset.services.validation_service import ValidationResult, validate_ready_metadata
from kws_testset.taxonomy import as_dict

EDITABLE_FIELDS = {
    "text",
    "sample_type",
    "quality_status",
    "voice_source",
    "speaker_id",
    "gender",
    "age_group",
    "volume",
    "pitch",
    "speed",
    "noise_scene",
    "snr_bucket",
    "impairment_type",
    "notes",
}


def asset_payload(item: AudioVariant, config: AppConfig) -> dict[str, Any]:
    validation = asset_validation_payload(item, config)
    return {
        "id": item.id,
        "source_id": item.source_id,
        "stored_path": item.stored_path,
        "text": item.text,
        "normalized_text": item.normalized_text,
        "sample_type": item.sample_type,
        "quality_status": item.quality_status,
        "voice_source": item.voice_source,
        "speaker_id": item.speaker_id,
        "gender": item.gender,
        "age_group": item.age_group,
        "volume": item.volume,
        "pitch": item.pitch,
        "speed": item.speed,
        "noise_scene": item.noise_scene,
        "snr_bucket": item.snr_bucket,
        "impairment_type": item.impairment_type,
        "variant_kind": item.variant_kind,
        "duration_sec": item.duration_sec,
        "sample_rate": item.sample_rate,
        "channels": item.channels,
        "notes": item.notes,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "validation": validation,
    }


def asset_validation_payload(item: AudioVariant, config: AppConfig) -> dict[str, Any]:
    result = validate_ready_metadata(asset_metadata_dict(item), item.duration_sec, config.app.target_keyword)
    return {"ok": result.ok, "errors": result.errors, "warnings": result.warnings}


def asset_metadata_dict(item: AudioVariant) -> dict[str, Any]:
    return {
        "text": item.text,
        "sample_type": item.sample_type,
        "quality_status": item.quality_status,
        "voice_source": item.voice_source,
        "gender": item.gender,
        "age_group": item.age_group,
        "volume": item.volume,
        "pitch": item.pitch,
        "speed": item.speed,
        "noise_scene": item.noise_scene,
        "impairment_type": item.impairment_type,
    }


def apply_asset_patch(item: AudioVariant, patch: dict[str, Any], config: AppConfig) -> ValidationResult:
    taxonomy = as_dict()
    for key, value in patch.items():
        if key not in EDITABLE_FIELDS:
            return ValidationResult(False, [f"field is not editable: {key}"], [])
        if key in taxonomy and value not in taxonomy[key]:
            return ValidationResult(False, [f"{key} has invalid value: {value}"], [])
        setattr(item, key, value)

    item.normalized_text = normalize_text(item.text)
    validation = validate_ready_metadata(asset_metadata_dict(item), item.duration_sec, config.app.target_keyword)
    if not validation.ok:
        return validation
    item.updated_at = datetime.now(timezone.utc)
    return validation
