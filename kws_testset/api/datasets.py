from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.models.dataset import DatasetItem, DatasetSpec, DatasetVersion, ManualOverride
from kws_testset.services.coverage_service import build_coverage_summary
from kws_testset.services.sampling_service import ManualOverrideInput, SampleCandidate, sample_candidates
from kws_testset.services.text_normalize import normalize_text
from kws_testset.utils.ids import new_id
from kws_testset.utils.paths import safe_child_dir

router = APIRouter(tags=["datasets"])

CANDIDATE_METADATA_FIELDS = {
    "voice_source",
    "speaker_id",
    "gender",
    "age_group",
    "volume",
    "pitch",
    "speed",
    "noise_scene",
    "impairment_type",
    "variant_kind",
    "snr_bucket",
}
FILTER_FIELDS = CANDIDATE_METADATA_FIELDS | {"quality_status", "sample_type"}
BALANCE_FIELDS = CANDIDATE_METADATA_FIELDS | {"sample_type"}


class DatasetSpecRequest(BaseModel):
    name: str
    description: str = ""
    target_keyword: str
    sampling_seed: int = 20260617
    quotas: dict[str, int]
    filters: dict[str, Any] = {}
    balance_by: list[str] = []
    min_duration_sec: float | None = None
    max_duration_sec: float | None = None


class OverrideRequest(BaseModel):
    variant_id: str
    action: str
    reason: str


def _variant_to_candidate(variant: AudioVariant) -> SampleCandidate:
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


def _validate_filter_config(filters: dict[str, Any]) -> None:
    for field, allowed in filters.items():
        if field not in FILTER_FIELDS:
            raise HTTPException(status_code=400, detail=f"unknown filter field: {field}")
        if not isinstance(allowed, list):
            raise HTTPException(status_code=400, detail=f"filter field must be a list: {field}")


def _validate_balance_by(balance_by: list[str]) -> None:
    for field in balance_by:
        if field not in BALANCE_FIELDS:
            raise HTTPException(status_code=400, detail=f"unknown balance_by field: {field}")


def _matches_filters(variant: AudioVariant, filters: dict[str, Any]) -> bool:
    for field, allowed in filters.items():
        if field == "quality_status":
            continue
        value = getattr(variant, field)
        if value is None:
            value = "unknown"
        if value not in allowed:
            return False
    return True


def _metadata_snapshot(variant: AudioVariant) -> dict[str, Any]:
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


@router.post("/api/dataset-specs")
def create_dataset_spec(payload: DatasetSpecRequest, request: Request) -> dict[str, Any]:
    _validate_filter_config(payload.filters)
    _validate_balance_by(payload.balance_by)
    spec = DatasetSpec(
        id=new_id("ds"),
        name=payload.name,
        description=payload.description,
        target_keyword=payload.target_keyword,
        target_keyword_normalized=normalize_text(payload.target_keyword),
        sampling_seed=payload.sampling_seed,
        quotas=payload.quotas,
        filters=payload.filters,
        balance_by=payload.balance_by,
        min_duration_sec=payload.min_duration_sec,
        max_duration_sec=payload.max_duration_sec,
    )
    with Session(request.app.state.engine) as session:
        session.add(spec)
        session.commit()
        session.refresh(spec)
    return {"id": spec.id, "name": spec.name, "quotas": spec.quotas}


@router.post("/api/dataset-specs/{spec_id}/overrides")
def create_manual_override(spec_id: str, payload: OverrideRequest, request: Request) -> dict[str, Any]:
    if payload.action not in {"include", "exclude"}:
        raise HTTPException(status_code=400, detail="action must be include or exclude")
    override = ManualOverride(
        id=new_id("ovr"),
        dataset_spec_id=spec_id,
        variant_id=payload.variant_id,
        action=payload.action,
        reason=payload.reason,
    )
    with Session(request.app.state.engine) as session:
        session.add(override)
        session.commit()
        session.refresh(override)
    return {"id": override.id, "dataset_spec_id": override.dataset_spec_id, "variant_id": override.variant_id, "action": override.action, "reason": override.reason}


@router.post("/api/dataset-specs/{spec_id}/build")
def build_dataset_version(spec_id: str, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")

        _validate_filter_config(spec.filters)
        _validate_balance_by(spec.balance_by)

        all_ready_variants = session.exec(select(AudioVariant).where(AudioVariant.quality_status == "ready").order_by(AudioVariant.id)).all()
        overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec_id).order_by(ManualOverride.id)).all()
        include_ids = {item.variant_id for item in overrides if item.action == "include"}
        include_variants_by_id: dict[str, AudioVariant] = {}
        if include_ids:
            include_variants = session.exec(select(AudioVariant).where(AudioVariant.id.in_(include_ids)).order_by(AudioVariant.id)).all()
            include_variants_by_id = {item.id: item for item in include_variants}
            missing_include_ids = sorted(include_ids - set(include_variants_by_id))
            if missing_include_ids:
                raise HTTPException(status_code=400, detail=f"manual include variant not found: {', '.join(missing_include_ids)}")
            not_ready_include_ids = sorted(item.id for item in include_variants if item.quality_status != "ready")
            if not_ready_include_ids:
                raise HTTPException(status_code=400, detail=f"manual include variant must be ready: {', '.join(not_ready_include_ids)}")
            wrong_type_include_ids = sorted(item.id for item in include_variants if item.sample_type not in spec.quotas)
            if wrong_type_include_ids:
                raise HTTPException(status_code=400, detail=f"manual include sample_type must be in quotas: {', '.join(wrong_type_include_ids)}")

        auto_variants = [item for item in all_ready_variants if _matches_filters(item, spec.filters)]
        if spec.min_duration_sec is not None:
            auto_variants = [item for item in auto_variants if item.duration_sec >= spec.min_duration_sec]
        if spec.max_duration_sec is not None:
            auto_variants = [item for item in auto_variants if item.duration_sec <= spec.max_duration_sec]
        auto_variants = [item for item in auto_variants if item.sample_type in spec.quotas]

        include_variants = [include_variants_by_id[item_id] for item_id in sorted(include_variants_by_id)]
        variants_by_id = {item.id: item for item in auto_variants}
        for item in include_variants:
            variants_by_id[item.id] = item
        variants = list(variants_by_id.values())
        candidates = [_variant_to_candidate(item) for item in variants]
        try:
            result = sample_candidates(
                candidates=candidates,
                quotas=spec.quotas,
                balance_by=spec.balance_by,
                seed=spec.sampling_seed,
                overrides=[ManualOverrideInput(item.variant_id, item.action, item.reason) for item in overrides],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        selected_by_id = {item.variant_id: item for item in result.items}
        selected_variants = [item for item in variants if item.id in selected_by_id]
        selected_variants.sort(key=lambda item: selected_by_id[item.id].selection_rank)

        existing_versions = session.exec(select(DatasetVersion).where(DatasetVersion.dataset_spec_id == spec_id)).all()
        version_number = max((item.version for item in existing_versions), default=0) + 1
        version_id = new_id("dsv")
        snapshots_by_variant_id = {item.id: _metadata_snapshot(item) for item in selected_variants}
        snapshots = [snapshots_by_variant_id[item.id] for item in selected_variants]
        coverage = build_coverage_summary(snapshots, spec.balance_by + ["sample_type"], result.shortfalls)
        version = DatasetVersion(
            id=version_id,
            dataset_spec_id=spec.id,
            version=version_number,
            name=f"{spec.name}_v{version_number:03d}",
            sampling_seed=spec.sampling_seed,
            rules_snapshot={
                "dataset_spec_id": spec.id,
                "name": spec.name,
                "target_keyword": spec.target_keyword,
                "target_keyword_normalized": spec.target_keyword_normalized,
                "quotas": spec.quotas,
                "filters": spec.filters,
                "balance_by": spec.balance_by,
                "min_duration_sec": spec.min_duration_sec,
                "max_duration_sec": spec.max_duration_sec,
                "overrides": [
                    {"variant_id": item.variant_id, "action": item.action, "reason": item.reason}
                    for item in sorted(overrides, key=lambda row: row.id)
                ],
                "shortfalls": result.shortfalls,
            },
            coverage_summary=coverage,
            item_count=len(selected_variants),
            total_duration_sec=sum(item.duration_sec for item in selected_variants),
            built_at=datetime.now(timezone.utc),
        )
        session.add(version)
        for variant in selected_variants:
            selected = selected_by_id[variant.id]
            item = DatasetItem(
                id=f"utt_{version.id}_{selected.selection_rank:06d}",
                dataset_version_id=version.id,
                variant_id=variant.id,
                sample_type=variant.sample_type,
                text=variant.text,
                normalized_text=variant.normalized_text,
                duration_sec=variant.duration_sec,
                selection_reason=selected.selection_reason,
                selection_rank=selected.selection_rank,
                metadata_snapshot=snapshots_by_variant_id[variant.id],
            )
            session.add(item)
        session.commit()
        session.refresh(version)

    return {
        "id": version.id,
        "name": version.name,
        "version": version.version,
        "item_count": version.item_count,
        "total_duration_sec": version.total_duration_sec,
        "coverage_summary": version.coverage_summary,
    }


@router.post("/api/dataset-versions/{version_id}/export")
def export_dataset_version(version_id: str, request: Request) -> dict[str, Any]:
    from kws_testset.services.export_service import ExportItem, export_dataset

    engine = request.app.state.engine
    config = request.app.state.config
    with Session(engine) as session:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="dataset version not found")
        spec = session.get(DatasetSpec, version.dataset_spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")
        items = session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == version_id)).all()
        export_items = [
            ExportItem(
                id=item.id,
                audio=str(item.metadata_snapshot.get("stored_path", "")),
                text=item.text,
                duration=item.duration_sec,
                sample_type=item.sample_type,
                metadata=item.metadata_snapshot,
            )
            for item in sorted(items, key=lambda row: row.selection_rank)
        ]
        export_root = config.app.data_dir / "exports"
        export_dir = safe_child_dir(export_root, f"{spec.name}_{spec.id}") / f"v{version.version:03d}_{new_id('exp')}"
        result = export_dataset(
            export_dir=export_dir,
            dataset_name=spec.name,
            version=version.version,
            target_keyword=spec.target_keyword,
            sampling_seed=version.sampling_seed,
            items=export_items,
            coverage_summary=version.coverage_summary,
        )
        version.export_path = str(result.export_dir.resolve())
        version.exported_at = datetime.now(timezone.utc)
        version.build_status = "exported"
        session.add(version)
        session.commit()
    return {
        "export_dir": str(result.export_dir),
        "manifest": str(result.manifest_path),
        "rich_manifest": str(result.rich_manifest_path),
        "dataset_yaml": str(result.dataset_yaml_path),
        "coverage_summary": str(result.coverage_summary_path),
        "eval_config_snippet": str(result.eval_config_snippet_path),
        "negative_hours": result.negative_hours,
    }
