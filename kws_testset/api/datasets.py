from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from kws_testset.models.dataset import DatasetItem, DatasetSpec, DatasetVersion, ManualOverride
from kws_testset.services.dataset_preview_service import preview_spec_selection
from kws_testset.services.dataset_selection_service import select_spec_samples
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


def _spec_payload(spec: DatasetSpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "description": spec.description,
        "target_keyword": spec.target_keyword,
        "target_keyword_normalized": spec.target_keyword_normalized,
        "sampling_seed": spec.sampling_seed,
        "status": spec.status,
        "quotas": spec.quotas,
        "filters": spec.filters,
        "balance_by": spec.balance_by,
        "min_duration_sec": spec.min_duration_sec,
        "max_duration_sec": spec.max_duration_sec,
        "created_at": spec.created_at.isoformat(),
        "updated_at": spec.updated_at.isoformat(),
    }


def _version_payload(version: DatasetVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "dataset_spec_id": version.dataset_spec_id,
        "version": version.version,
        "name": version.name,
        "build_status": version.build_status,
        "sampling_seed": version.sampling_seed,
        "rules_snapshot": version.rules_snapshot,
        "coverage_summary": version.coverage_summary,
        "item_count": version.item_count,
        "total_duration_sec": version.total_duration_sec,
        "export_path": version.export_path,
        "created_at": version.created_at.isoformat(),
        "built_at": version.built_at.isoformat() if version.built_at else None,
        "exported_at": version.exported_at.isoformat() if version.exported_at else None,
    }


def _item_payload(item: DatasetItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "dataset_version_id": item.dataset_version_id,
        "variant_id": item.variant_id,
        "sample_type": item.sample_type,
        "text": item.text,
        "normalized_text": item.normalized_text,
        "duration_sec": item.duration_sec,
        "selection_reason": item.selection_reason,
        "selection_rank": item.selection_rank,
        "metadata_snapshot": item.metadata_snapshot,
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

        try:
            selection = select_spec_samples(spec, session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        overrides = selection.overrides
        selected_by_id = selection.selected_by_id
        selected_variants = selection.selected_variants

        existing_versions = session.exec(select(DatasetVersion).where(DatasetVersion.dataset_spec_id == spec_id)).all()
        version_number = max((item.version for item in existing_versions), default=0) + 1
        version_id = new_id("dsv")
        snapshots_by_variant_id = {item["variant_id"]: item for item in selection.snapshots}
        coverage = selection.coverage_summary
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
                "shortfalls": selection.result.shortfalls,
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


@router.get("/api/dataset-specs")
def list_dataset_specs(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        specs = session.exec(select(DatasetSpec).order_by(DatasetSpec.created_at.desc())).all()
    return {"items": [_spec_payload(spec) for spec in specs]}


@router.get("/api/dataset-specs/{spec_id}")
def get_dataset_spec(spec_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")
        overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec_id).order_by(ManualOverride.id)).all()
    payload = _spec_payload(spec)
    payload["overrides"] = [
        {"id": item.id, "variant_id": item.variant_id, "action": item.action, "reason": item.reason, "created_at": item.created_at.isoformat()}
        for item in overrides
    ]
    return payload


@router.post("/api/dataset-specs/{spec_id}/preview")
def preview_dataset_spec(spec_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")
        _validate_filter_config(spec.filters)
        _validate_balance_by(spec.balance_by)
        try:
            return preview_spec_selection(spec, session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/dataset-versions")
def list_dataset_versions(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        versions = session.exec(select(DatasetVersion).order_by(DatasetVersion.created_at.desc())).all()
    return {"items": [_version_payload(version) for version in versions]}


@router.get("/api/dataset-versions/{version_id}")
def get_dataset_version(version_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        version = session.get(DatasetVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="dataset version not found")
    return _version_payload(version)


@router.get("/api/dataset-versions/{version_id}/items")
def list_dataset_version_items(version_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="dataset version not found")
        items = session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == version_id).order_by(DatasetItem.selection_rank)).all()
    return {"items": [_item_payload(item) for item in items]}


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
