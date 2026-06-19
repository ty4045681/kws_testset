from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import wave

from fastapi import UploadFile
from sqlmodel import Session, select

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioSource
from kws_testset.services.audio_probe import probe_wav
from kws_testset.utils.ids import new_id


@dataclass(frozen=True)
class UploadedAudioRow:
    path: Path
    original_filename: str
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str
    status: str
    error: str | None = None


def safe_upload_filename(filename: str) -> str:
    name = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not cleaned:
        cleaned = "upload.wav"
    return cleaned


def save_uploads(files: list[UploadFile], config: AppConfig, session: Session) -> tuple[str, list[UploadedAudioRow]]:
    upload_id = new_id("upl")
    upload_dir = config.app.data_dir / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    rows: list[UploadedAudioRow] = []

    for index, upload in enumerate(files):
        original_filename = upload.filename or f"upload_{index}.wav"
        filename = safe_upload_filename(original_filename)
        destination = upload_dir / filename

        if not filename.lower().endswith(".wav"):
            rows.append(
                UploadedAudioRow(
                    path=destination,
                    original_filename=original_filename,
                    duration_sec=0.0,
                    sample_rate=0,
                    channels=0,
                    bit_depth=0,
                    sha256="",
                    status="error",
                    error="Only WAV files are supported",
                )
            )
            continue

        with destination.open("wb") as output:
            shutil.copyfileobj(upload.file, output)

        try:
            probe = probe_wav(destination)
        except (OSError, EOFError, ValueError, wave.Error) as exc:
            rows.append(
                UploadedAudioRow(
                    path=destination,
                    original_filename=filename,
                    duration_sec=0.0,
                    sample_rate=0,
                    channels=0,
                    bit_depth=0,
                    sha256="",
                    status="error",
                    error=f"Invalid WAV file: {exc}",
                )
            )
            continue

        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        status = "duplicate" if existing else "can_import"
        rows.append(
            UploadedAudioRow(
                path=probe.path,
                original_filename=filename,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                bit_depth=probe.bit_depth,
                sha256=probe.sha256,
                status=status,
            )
        )

    return upload_id, rows
