from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kws_testset.taxonomy import (
    AGE_GROUPS,
    GENDERS,
    IMPAIRMENT_TYPES,
    NOISE_SCENES,
    PITCHES,
    QUALITY_STATUSES,
    SAMPLE_TYPES,
    SPEEDS,
    VOICE_SOURCES,
    VOLUMES,
)
from kws_testset.services.text_normalize import contains_keyword


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_sample_semantics(text: str, sample_type: str, target_keyword: str) -> ValidationResult:
    errors: list[str] = []
    if sample_type not in SAMPLE_TYPES:
        errors.append(f"unknown sample_type: {sample_type}")
        return ValidationResult(ok=False, errors=errors, warnings=[])

    has_keyword = contains_keyword(text, target_keyword)
    if sample_type == "wake_positive" and not has_keyword:
        errors.append("wake_positive text must contain target keyword")
    if sample_type in {"similar_negative", "partial_wake", "ordinary_negative"} and has_keyword:
        errors.append(f"{sample_type} text must not contain target keyword")
    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=[])


def validate_file_exists(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(ok=False, errors=[f"file does not exist: {path}"], warnings=[])
    if not path.is_file():
        return ValidationResult(ok=False, errors=[f"path is not a file: {path}"], warnings=[])
    return ValidationResult(ok=True, errors=[], warnings=[])


def validate_ready_metadata(metadata: dict[str, object], duration_sec: float, target_keyword: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    quality_status = str(metadata.get("quality_status", "draft"))
    if quality_status not in QUALITY_STATUSES:
        errors.append(f"unknown quality_status: {quality_status}")
    if quality_status != "ready":
        return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)

    text = str(metadata.get("text", ""))
    if not text.strip():
        errors.append("ready text is required")
    if duration_sec <= 0:
        errors.append("ready duration_sec must be greater than 0")

    enum_fields = {
        "sample_type": SAMPLE_TYPES,
        "voice_source": VOICE_SOURCES,
        "gender": GENDERS,
        "age_group": AGE_GROUPS,
        "volume": VOLUMES,
        "pitch": PITCHES,
        "speed": SPEEDS,
        "noise_scene": NOISE_SCENES,
        "impairment_type": IMPAIRMENT_TYPES,
    }
    for field, allowed in enum_fields.items():
        value = str(metadata.get(field, ""))
        if value not in allowed:
            errors.append(f"ready {field} has invalid value: {value}")

    for field in ["voice_source", "volume", "pitch", "speed", "impairment_type"]:
        if str(metadata.get(field, "unknown")) == "unknown":
            errors.append(f"ready {field} must not be unknown")

    if text.strip() and str(metadata.get("sample_type", "")) in SAMPLE_TYPES:
        semantic = validate_sample_semantics(text, str(metadata.get("sample_type")), target_keyword)
        errors.extend(semantic.errors)
        warnings.extend(semantic.warnings)

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)
