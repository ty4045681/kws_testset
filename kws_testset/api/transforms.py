from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from kws_testset.models.transform_job import TransformJob
from kws_testset.services.transform_job_service import create_transform_job, transform_job_payload

router = APIRouter(prefix="/api/transform-jobs", tags=["transform-jobs"])


class CreateTransformJobRequest(BaseModel):
    variant_ids: list[str]
    transform_kind: str
    params: dict[str, Any] = {}


@router.get("")
def list_transform_jobs(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        jobs = session.exec(select(TransformJob).order_by(TransformJob.created_at.desc())).all()
    return {"items": [transform_job_payload(job) for job in jobs]}


@router.post("")
def create_transform_job_endpoint(payload: CreateTransformJobRequest, request: Request) -> dict[str, Any]:
    try:
        with Session(request.app.state.engine) as session:
            job = create_transform_job(
                variant_ids=payload.variant_ids,
                transform_kind=payload.transform_kind,
                params=payload.params,
                config=request.app.state.config,
                session=session,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return transform_job_payload(job)


@router.get("/{job_id}")
def get_transform_job(job_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        job = session.get(TransformJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="transform job not found")
    return transform_job_payload(job)
