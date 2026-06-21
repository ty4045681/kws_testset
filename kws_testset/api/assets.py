from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.services.asset_service import apply_asset_patch, asset_payload

router = APIRouter(prefix="/api/assets", tags=["assets"])

FILTERABLE_FIELDS = {
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
    "variant_kind",
}
CONTROL_QUERY_PARAMS = {"limit", "offset"}


class AssetPatchRequest(BaseModel):
    text: str | None = None
    sample_type: str | None = None
    quality_status: str | None = None
    voice_source: str | None = None
    speaker_id: str | None = None
    gender: str | None = None
    age_group: str | None = None
    volume: str | None = None
    pitch: str | None = None
    speed: str | None = None
    noise_scene: str | None = None
    snr_bucket: str | None = None
    impairment_type: str | None = None
    notes: str | None = None


class BulkUpdateRequest(BaseModel):
    asset_ids: list[str]
    patch: dict[str, Any]


def _extract_patch(payload: AssetPatchRequest) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


@router.get("")
def list_assets(request: Request, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    query = select(AudioVariant)
    count_query = select(func.count()).select_from(AudioVariant)
    query_params = dict(request.query_params)
    for field, value in query_params.items():
        if field in CONTROL_QUERY_PARAMS:
            continue
        if field not in FILTERABLE_FIELDS:
            raise HTTPException(status_code=400, detail=f"unknown asset filter: {field}")
        if field in FILTERABLE_FIELDS:
            condition = getattr(AudioVariant, field) == value
            query = query.where(condition)
            count_query = count_query.where(condition)
    query = query.order_by(AudioVariant.created_at, AudioVariant.id).offset(offset).limit(limit)
    with Session(engine) as session:
        variants = session.exec(query).all()
        total = session.exec(count_query).one()
    return {"items": [asset_payload(item, config) for item in variants], "limit": limit, "offset": offset, "count": len(variants), "total": total}


@router.post("/bulk-update")
def bulk_update_assets(payload: BulkUpdateRequest, request: Request) -> dict[str, Any]:
    config = request.app.state.config
    results: dict[str, Any] = {}
    updated = 0
    failed = 0
    asset_ids = list(dict.fromkeys(payload.asset_ids))
    with Session(request.app.state.engine) as session:
        for asset_id in asset_ids:
            savepoint = session.begin_nested()
            try:
                item = session.get(AudioVariant, asset_id)
                if item is None:
                    savepoint.rollback()
                    failed += 1
                    results[asset_id] = {"ok": False, "errors": ["asset not found"], "warnings": []}
                    continue
                validation = apply_asset_patch(item, payload.patch, config)
                if not validation.ok:
                    savepoint.rollback()
                    failed += 1
                    results[asset_id] = {"ok": False, "errors": validation.errors, "warnings": validation.warnings}
                    continue
                session.add(item)
                savepoint.commit()
                updated += 1
                results[asset_id] = {"ok": True, "errors": [], "warnings": validation.warnings}
            except Exception as exc:
                savepoint.rollback()
                failed += 1
                results[asset_id] = {"ok": False, "errors": [f"unexpected error: {exc}"], "warnings": []}
        session.commit()
    return {"updated": updated, "failed": failed, "results": results}


@router.get("/{asset_id}/audio")
def stream_asset_audio(asset_id: str, request: Request) -> FileResponse:
    with Session(request.app.state.engine) as session:
        item = session.get(AudioVariant, asset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="asset not found")
    path = Path(item.stored_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="audio file not found")
    return FileResponse(path, media_type="audio/wav", filename=path.name)


@router.patch("/{asset_id}")
def patch_asset(asset_id: str, payload: AssetPatchRequest, request: Request) -> dict[str, Any]:
    config = request.app.state.config
    with Session(request.app.state.engine) as session:
        item = session.get(AudioVariant, asset_id)
        if item is None:
            raise HTTPException(status_code=404, detail="asset not found")
        validation = apply_asset_patch(item, _extract_patch(payload), config)
        if not validation.ok:
            session.rollback()
            raise HTTPException(status_code=400, detail={"errors": validation.errors, "warnings": validation.warnings})
        session.add(item)
        session.commit()
        session.refresh(item)
        return {"asset": asset_payload(item, config), "validation": {"ok": validation.ok, "errors": validation.errors, "warnings": validation.warnings}}
