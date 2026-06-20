from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioVariant
from kws_testset.models.transform_job import TransformJob
from kws_testset.services.audio_probe import probe_wav
from kws_testset.services.audio_transform_service import SUPPORTED_TRANSFORM_KINDS, apply_audio_transform
from kws_testset.utils.ids import dated_id, new_id


def transform_job_payload(job: TransformJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "transform_kind": job.transform_kind,
        "status": job.status,
        "input_variant_ids": job.input_variant_ids,
        "processing_params": job.processing_params,
        "requested_count": job.requested_count,
        "created_count": job.created_count,
        "failed_count": job.failed_count,
        "created_variant_ids": job.created_variant_ids,
        "results": job.results,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _job_status(created_count: int, failed_count: int) -> str:
    if failed_count == 0:
        return "completed"
    if created_count > 0:
        return "partial"
    return "failed"


def _processing_record(transform_kind: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"transform_kind": transform_kind, "params": params}


def _variant_metadata(parent: AudioVariant, transform_kind: str, params: dict[str, Any]) -> dict[str, Any]:
    volume = parent.volume
    speed = parent.speed
    noise_scene = parent.noise_scene
    snr_bucket = parent.snr_bucket
    if transform_kind == "volume_gain":
        gain_db = float(params.get("gain_db", 0.0))
        volume = "high" if gain_db > 0 else "low"
    if transform_kind == "speed_change":
        speed_factor = float(params.get("speed_factor", 1.0))
        speed = "fast" if speed_factor > 1 else "slow"
    if transform_kind == "noise_mix":
        noise_scene = str(params.get("noise_scene", "other"))
        snr_bucket = str(params.get("snr_bucket", "unknown"))
    return {"volume": volume, "speed": speed, "noise_scene": noise_scene, "snr_bucket": snr_bucket}


def _create_child_variant(
    parent: AudioVariant,
    transformed_path: Path,
    transform_kind: str,
    params: dict[str, Any],
    session: Session,
) -> AudioVariant:
    probe = probe_wav(transformed_path)
    existing = session.exec(select(AudioVariant).where(AudioVariant.sha256 == probe.sha256)).first()
    if existing is not None:
        raise ValueError(f"generated variant already exists: {existing.id}")

    variant_id = dated_id("var", probe.sha256)
    final_path = transformed_path.parent / f"{variant_id}.wav"
    transformed_path.replace(final_path)
    probe = probe_wav(final_path)
    record = _processing_record(transform_kind, params)
    metadata = _variant_metadata(parent, transform_kind, params)
    child = AudioVariant(
        id=variant_id,
        source_id=parent.source_id,
        parent_variant_id=parent.id,
        variant_kind=transform_kind,
        stored_path=str(final_path.resolve()),
        sha256=probe.sha256,
        duration_sec=probe.duration_sec,
        sample_rate=probe.sample_rate,
        channels=probe.channels,
        text=parent.text,
        normalized_text=parent.normalized_text,
        sample_type=parent.sample_type,
        quality_status="draft",
        voice_source=parent.voice_source,
        speaker_id=parent.speaker_id,
        gender=parent.gender,
        age_group=parent.age_group,
        volume=metadata["volume"],
        pitch=parent.pitch,
        speed=metadata["speed"],
        noise_scene=metadata["noise_scene"],
        snr_bucket=metadata["snr_bucket"],
        impairment_type=parent.impairment_type,
        impairment_chain=[*parent.impairment_chain, record],
        processing_params=record,
        custom_tags=list(parent.custom_tags),
        notes=f"Generated from {parent.id} by {transform_kind}",
    )
    session.add(child)
    return child


def create_transform_job(
    variant_ids: list[str],
    transform_kind: str,
    params: dict[str, Any],
    config: AppConfig,
    session: Session,
) -> TransformJob:
    if transform_kind not in SUPPORTED_TRANSFORM_KINDS:
        raise ValueError(f"unknown transform_kind: {transform_kind}")
    if not variant_ids:
        raise ValueError("variant_ids must not be empty")

    job = TransformJob(
        id=new_id("tfm"),
        transform_kind=transform_kind,
        status="running",
        input_variant_ids=variant_ids,
        processing_params=params,
        requested_count=len(variant_ids),
    )
    session.add(job)

    variants_root = config.app.data_dir / "library" / "variants"
    variants_root.mkdir(parents=True, exist_ok=True)
    created_variant_ids: list[str] = []
    results: list[dict[str, Any]] = []
    created_count = 0
    failed_count = 0

    for variant_id in variant_ids:
        temp_path: Path | None = None
        savepoint = session.begin_nested()
        try:
            parent = session.get(AudioVariant, variant_id)
            if parent is None:
                savepoint.rollback()
                failed_count += 1
                results.append(
                    {"input_variant_id": variant_id, "status": "error", "created_variant_id": None, "errors": ["variant not found"]}
                )
                continue

            temp_path = variants_root / f"{new_id('tmp')}.wav"
            apply_audio_transform(Path(parent.stored_path), temp_path, transform_kind, params)
            child = _create_child_variant(parent, temp_path, transform_kind, params, session)
            session.flush()
            savepoint.commit()
            created_count += 1
            created_variant_ids.append(child.id)
            results.append({"input_variant_id": variant_id, "status": "created", "created_variant_id": child.id, "errors": []})
        except Exception as exc:
            savepoint.rollback()
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            failed_count += 1
            results.append({"input_variant_id": variant_id, "status": "error", "created_variant_id": None, "errors": [str(exc)]})

    job.created_variant_ids = created_variant_ids
    job.results = results
    job.created_count = created_count
    job.failed_count = failed_count
    job.status = _job_status(created_count, failed_count)
    job.completed_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
