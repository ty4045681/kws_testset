from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
import wave
from typing import Any

from sqlmodel import Session, select

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioSource, AudioVariant
from kws_testset.models.import_batch import ImportBatch
from kws_testset.services.audio_probe import probe_wav
from kws_testset.services.text_normalize import normalize_text
from kws_testset.services.validation_service import validate_ready_metadata, validate_sample_semantics
from kws_testset.utils.ids import dated_id, new_id


@dataclass(frozen=True)
class ScannedAudioFile:
    path: Path
    original_filename: str
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str
    status: str


def _expand_wav_inputs(paths: list[str]) -> list[Path]:
    expanded: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if path.is_dir():
            expanded.extend(sorted(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() == ".wav"))
        else:
            expanded.append(path)
    return expanded


def scan_wav_paths(paths: list[str], session: Session) -> list[ScannedAudioFile]:
    results: list[ScannedAudioFile] = []
    for path in _expand_wav_inputs(paths):
        try:
            probe = probe_wav(path)
        except (OSError, EOFError, wave.Error):
            results.append(
                ScannedAudioFile(
                    path=path,
                    original_filename=path.name,
                    duration_sec=0.0,
                    sample_rate=0,
                    channels=0,
                    bit_depth=0,
                    sha256="",
                    status="error",
                )
            )
            continue
        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        status = "duplicate" if existing else "can_import"
        results.append(
            ScannedAudioFile(
                path=probe.path,
                original_filename=probe.path.name,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                bit_depth=probe.bit_depth,
                sha256=probe.sha256,
                status=status,
            )
        )
    return results


def commit_import_batch(name: str, files: list[dict[str, Any]], config: AppConfig, session: Session) -> ImportBatch:
    batch_id = new_id("imp")
    batch = ImportBatch(id=batch_id, name=name, file_count=len(files), status="imported")
    session.add(batch)

    source_root = config.app.data_dir / "library" / "sources"
    source_root.mkdir(parents=True, exist_ok=True)

    imported_count = 0
    duplicate_count = 0
    for item in files:
        probe = probe_wav(item["path"])
        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        if existing:
            duplicate_count += 1
            continue

        semantic = validate_sample_semantics(item["text"], item["sample_type"], config.app.target_keyword)
        if not semantic.ok:
            raise ValueError("; ".join(semantic.errors))
        ready_check = validate_ready_metadata(item, probe.duration_sec, config.app.target_keyword)
        if not ready_check.ok:
            raise ValueError("; ".join(ready_check.errors))

        source_id = dated_id("src", probe.sha256)
        variant_id = dated_id("var", probe.sha256)
        stored_path = source_root / f"{source_id}.wav"
        shutil.copy2(probe.path, stored_path)

        source = AudioSource(
            id=source_id,
            original_filename=probe.path.name,
            stored_path=str(stored_path.resolve()),
            sha256=probe.sha256,
            duration_sec=probe.duration_sec,
            sample_rate=probe.sample_rate,
            channels=probe.channels,
            bit_depth=probe.bit_depth,
            import_batch_id=batch_id,
        )
        variant = AudioVariant(
            id=variant_id,
            source_id=source_id,
            variant_kind="original",
            stored_path=str(stored_path.resolve()),
            sha256=probe.sha256,
            duration_sec=probe.duration_sec,
            sample_rate=probe.sample_rate,
            channels=probe.channels,
            text=item["text"],
            normalized_text=normalize_text(item["text"]),
            sample_type=item["sample_type"],
            quality_status=item.get("quality_status", "draft"),
            voice_source=item.get("voice_source", "unknown"),
            gender=item.get("gender", "unknown"),
            age_group=item.get("age_group", "unknown"),
            volume=item.get("volume", "unknown"),
            pitch=item.get("pitch", "unknown"),
            speed=item.get("speed", "unknown"),
            noise_scene=item.get("noise_scene", "unknown"),
            impairment_type=item.get("impairment_type", "none"),
            notes=item.get("notes"),
        )
        session.add(source)
        session.add(variant)
        imported_count += 1

    batch.imported_count = imported_count
    batch.duplicate_count = duplicate_count
    batch.completed_at = datetime.now(timezone.utc)
    session.add(batch)
    session.commit()
    session.refresh(batch)
    return batch
