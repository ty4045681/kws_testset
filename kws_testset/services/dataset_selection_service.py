from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.models.dataset import DatasetSpec, ManualOverride
from kws_testset.services.coverage_service import build_coverage_summary
from kws_testset.services.sampling_service import ManualOverrideInput, SampleCandidate, SamplingResult, SelectedSample, sample_candidates


@dataclass(frozen=True)
class SpecSelection:
    variants: list[AudioVariant]
    selected_variants: list[AudioVariant]
    selected_by_id: dict[str, SelectedSample]
    overrides: list[ManualOverride]
    snapshots: list[dict[str, Any]]
    result: SamplingResult
    coverage_summary: dict[str, Any]


def variant_to_candidate(variant: AudioVariant) -> SampleCandidate:
    return SampleCandidate(
        id=variant.id,
        sample_type=variant.sample_type,
        duration_sec=variant.duration_sec,
        metadata={
            "sample_type": variant.sample_type,
            "voice_source": variant.voice_source,
            "speaker_id": variant.speaker_id or "unknown",
            "gender": variant.gender,
            "age_group": variant.age_group,
            "volume": variant.volume,
            "pitch": variant.pitch,
            "speed": variant.speed,
            "noise_scene": variant.noise_scene,
            "impairment_type": variant.impairment_type,
            "variant_kind": variant.variant_kind,
            "snr_bucket": variant.snr_bucket or "unknown",
        },
    )


def metadata_snapshot(variant: AudioVariant) -> dict[str, Any]:
    return {
        "variant_id": variant.id,
        "source_id": variant.source_id,
        "stored_path": variant.stored_path,
        "text": variant.text,
        "normalized_text": variant.normalized_text,
        "sample_type": variant.sample_type,
        "voice_source": variant.voice_source,
        "speaker_id": variant.speaker_id,
        "gender": variant.gender,
        "age_group": variant.age_group,
        "volume": variant.volume,
        "pitch": variant.pitch,
        "speed": variant.speed,
        "noise_scene": variant.noise_scene,
        "impairment_type": variant.impairment_type,
        "variant_kind": variant.variant_kind,
        "duration_sec": variant.duration_sec,
    }


def matches_filters(variant: AudioVariant, filters: dict[str, Any]) -> bool:
    for field, allowed in filters.items():
        if field == "quality_status":
            continue
        value = getattr(variant, field)
        if value is None:
            value = "unknown"
        if value not in allowed:
            return False
    return True


def select_spec_samples(spec: DatasetSpec, session: Session) -> SpecSelection:
    ready_variants = session.exec(select(AudioVariant).where(AudioVariant.quality_status == "ready").order_by(AudioVariant.id)).all()
    overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec.id).order_by(ManualOverride.id)).all()
    include_ids = {item.variant_id for item in overrides if item.action == "include"}
    include_variants_by_id: dict[str, AudioVariant] = {}
    if include_ids:
        include_variants = session.exec(select(AudioVariant).where(AudioVariant.id.in_(include_ids)).order_by(AudioVariant.id)).all()
        include_variants_by_id = {item.id: item for item in include_variants}
        missing_include_ids = sorted(include_ids - set(include_variants_by_id))
        if missing_include_ids:
            raise ValueError(f"manual include variant not found: {', '.join(missing_include_ids)}")
        not_ready_include_ids = sorted(item.id for item in include_variants if item.quality_status != "ready")
        if not_ready_include_ids:
            raise ValueError(f"manual include variant must be ready: {', '.join(not_ready_include_ids)}")
        wrong_type_include_ids = sorted(item.id for item in include_variants if item.sample_type not in spec.quotas)
        if wrong_type_include_ids:
            raise ValueError(f"manual include sample_type must be in quotas: {', '.join(wrong_type_include_ids)}")

    auto_variants = [item for item in ready_variants if matches_filters(item, spec.filters)]
    if spec.min_duration_sec is not None:
        auto_variants = [item for item in auto_variants if item.duration_sec >= spec.min_duration_sec]
    if spec.max_duration_sec is not None:
        auto_variants = [item for item in auto_variants if item.duration_sec <= spec.max_duration_sec]
    auto_variants = [item for item in auto_variants if item.sample_type in spec.quotas]

    variants_by_id = {item.id: item for item in auto_variants}
    for item_id in sorted(include_variants_by_id):
        variants_by_id[item_id] = include_variants_by_id[item_id]
    variants = list(variants_by_id.values())
    candidates = [variant_to_candidate(item) for item in variants]
    result = sample_candidates(
        candidates=candidates,
        quotas=spec.quotas,
        balance_by=spec.balance_by,
        seed=spec.sampling_seed,
        overrides=[ManualOverrideInput(item.variant_id, item.action, item.reason) for item in overrides],
    )
    selected_by_id = {item.variant_id: item for item in result.items}
    selected_variants = [item for item in variants if item.id in selected_by_id]
    selected_variants.sort(key=lambda item: selected_by_id[item.id].selection_rank)
    snapshots = [metadata_snapshot(item) for item in selected_variants]
    coverage = build_coverage_summary(snapshots, spec.balance_by + ["sample_type"], result.shortfalls)
    return SpecSelection(
        variants=variants,
        selected_variants=selected_variants,
        selected_by_id=selected_by_id,
        overrides=overrides,
        snapshots=snapshots,
        result=result,
        coverage_summary=coverage,
    )
