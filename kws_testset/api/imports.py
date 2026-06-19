from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from kws_testset.models.import_batch import ImportBatch
from kws_testset.services.import_service import commit_import_batch, commit_import_batch_partial, scan_wav_paths
from kws_testset.services.import_upload_service import save_uploads

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
    partial: bool = False


def _batch_payload(batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "name": batch.name,
        "source_directory": batch.source_directory,
        "file_count": batch.file_count,
        "imported_count": batch.imported_count,
        "duplicate_count": batch.duplicate_count,
        "status": batch.status,
        "created_at": batch.created_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


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
    if payload.partial:
        with Session(engine) as session:
            result = commit_import_batch_partial(
                name=payload.name,
                files=[item.model_dump() for item in payload.files],
                config=config,
                session=session,
            )
        batch = result.batch
        return {
            "id": batch.id,
            "name": batch.name,
            "imported_count": batch.imported_count,
            "duplicate_count": batch.duplicate_count,
            "failed_count": sum(1 for item in result.files if item.status == "error"),
            "status": batch.status,
            "files": [
                {"path": item.path, "status": item.status, "errors": item.errors}
                for item in result.files
            ],
        }

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
        "failed_count": 0,
        "status": batch.status,
        "files": [],
    }


@router.post("/uploads")
def upload_import_files(request: Request, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    with Session(engine) as session:
        upload_id, rows = save_uploads(files, config, session)
    return {
        "upload_id": upload_id,
        "uploaded": sum(1 for row in rows if row.status in {"can_import", "duplicate"}),
        "failed": sum(1 for row in rows if row.status == "error"),
        "files": [
            {
                "path": str(row.path),
                "original_filename": row.original_filename,
                "duration_sec": row.duration_sec,
                "sample_rate": row.sample_rate,
                "channels": row.channels,
                "bit_depth": row.bit_depth,
                "sha256": row.sha256,
                "status": row.status,
                "error": row.error,
            }
            for row in rows
        ],
    }


@router.get("")
def list_import_batches(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        batches = session.exec(select(ImportBatch).order_by(ImportBatch.created_at.desc())).all()
    return {"items": [_batch_payload(batch) for batch in batches]}


@router.get("/{batch_id}")
def get_import_batch(batch_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import batch not found")
    return _batch_payload(batch)
