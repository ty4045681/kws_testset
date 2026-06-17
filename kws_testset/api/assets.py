from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _asset_payload(item: AudioVariant) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "stored_path": item.stored_path,
        "text": item.text,
        "normalized_text": item.normalized_text,
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
        "duration_sec": item.duration_sec,
    }


@router.get("")
def list_assets(request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        variants = session.exec(select(AudioVariant).order_by(AudioVariant.created_at)).all()
    return {"items": [_asset_payload(item) for item in variants]}
