from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import wave

from kws_testset.utils.hashing import sha256_file


@dataclass(frozen=True)
class AudioProbe:
    path: Path
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str


def probe_wav(path: str | Path) -> AudioProbe:
    wav_path = Path(path).expanduser().resolve()
    with wave.open(str(wav_path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frame_count = wav.getnframes()
    if sample_rate <= 0:
        raise ValueError(f"invalid WAV sample_rate: {sample_rate}")
    duration_sec = frame_count / float(sample_rate)
    return AudioProbe(
        path=wav_path,
        duration_sec=duration_sec,
        sample_rate=sample_rate,
        channels=channels,
        bit_depth=sample_width * 8,
        sha256=sha256_file(wav_path),
    )
