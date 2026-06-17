from pathlib import Path
import math
import wave

from kws_testset.services.audio_probe import probe_wav
from kws_testset.utils.hashing import sha256_file


def write_silent_wav(path: Path, sample_rate: int = 16000, seconds: float = 0.25) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)


def test_probe_wav_reads_duration_sample_rate_channels_and_hash(tmp_path: Path):
    wav_path = tmp_path / "sample.wav"
    write_silent_wav(wav_path)

    info = probe_wav(wav_path)

    assert info.path == wav_path.resolve()
    assert math.isclose(info.duration_sec, 0.25, abs_tol=0.01)
    assert info.sample_rate == 16000
    assert info.channels == 1
    assert info.bit_depth == 16
    assert info.sha256 == sha256_file(wav_path)
