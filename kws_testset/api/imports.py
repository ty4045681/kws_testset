from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

from kws_testset.services.import_service import commit_import_batch, scan_wav_paths

router = APIRouter(prefix="/api/imports", tags=["imports"])


class ScanRequest(BaseModel):
    paths: list[str]


class ImportFileRequest(BaseModel):
    path: str
    text: str
    sample_type: str
    quality_status: str = "draft"
    voice_source: str = "unknown"
    gender: str = "unknown"
    age_group: str = "unknown"
    volume: str = "unknown"
    pitch: str = "unknown"
    speed: str = "unknown"
    noise_scene: str = "unknown"
    impairment_type: str = "none"
    notes: str | None = None


class CommitImportRequest(BaseModel):
    name: str
    files: list[ImportFileRequest]


@router.post("/scan")
def scan_imports(payload: ScanRequest, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        files = scan_wav_paths(payload.paths, session)
    return {
        "scanned": len(files),
        "files": [
            {
                "path": str(item.path),
                "original_filename": item.original_filename,
                "duration_sec": item.duration_sec,
                "sample_rate": item.sample_rate,
                "channels": item.channels,
                "bit_depth": item.bit_depth,
                "sha256": item.sha256,
                "status": item.status,
            }
            for item in files
        ],
    }


@router.post("")
def commit_import(payload: CommitImportRequest, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    try:
        with Session(engine) as session:
            batch = commit_import_batch(
                name=payload.name,
                files=[item.model_dump() for item in payload.files],
                config=config,
                session=session,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": batch.id,
        "name": batch.name,
        "imported_count": batch.imported_count,
        "duplicate_count": batch.duplicate_count,
        "status": batch.status,
    }
