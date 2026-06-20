from __future__ import annotations

from pathlib import Path
import wave

import numpy as np

from kws_testset.services.audio_probe import probe_wav
from kws_testset.services.audio_transform_service import apply_audio_transform


SAMPLE_RATE = 16000


def _write_pcm16(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    clipped = np.clip(np.round(samples), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(clipped.tobytes())


def _read_pcm16(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64)


def _sine(freq_hz: float, seconds: float = 0.25, amplitude: float = 9000.0) -> np.ndarray:
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def _high_frequency_energy(samples: np.ndarray, threshold_hz: float = 3000.0) -> float:
    spectrum = np.fft.rfft(samples)
    freqs = np.fft.rfftfreq(samples.size, d=1 / SAMPLE_RATE)
    return float(np.sum(np.abs(spectrum[freqs >= threshold_hz]) ** 2))


def test_band_limit_reduces_high_frequency_energy(tmp_path: Path):
    source = tmp_path / "mixed.wav"
    output = tmp_path / "limited.wav"
    samples = _sine(500) + _sine(6000)
    _write_pcm16(source, samples)

    apply_audio_transform(source, output, "band_limit", {"mode": "freq", "cutoff_hz": 2000})

    limited = _read_pcm16(output)
    assert probe_wav(output).sample_rate == SAMPLE_RATE
    assert _high_frequency_energy(limited) < _high_frequency_energy(samples) * 0.2


def test_subband_eq_is_deterministic_with_seed_and_changes_audio(tmp_path: Path):
    source = tmp_path / "tone.wav"
    first = tmp_path / "subband_first.wav"
    second = tmp_path / "subband_second.wav"
    samples = _sine(350) + _sine(1800) + _sine(4200)
    _write_pcm16(source, samples)

    params = {"seed": 42}
    apply_audio_transform(source, first, "subband_eq", params)
    apply_audio_transform(source, second, "subband_eq", params)

    assert first.read_bytes() == second.read_bytes()
    assert not np.array_equal(_read_pcm16(source), _read_pcm16(first))


def test_narrowband_preserves_rate_and_duration_while_changing_audio(tmp_path: Path):
    source = tmp_path / "wide.wav"
    output = tmp_path / "narrow.wav"
    samples = _sine(700) + _sine(5200)
    _write_pcm16(source, samples)

    apply_audio_transform(source, output, "narrowband", {"target_sample_rate": 8000})

    original_probe = probe_wav(source)
    output_probe = probe_wav(output)
    assert output_probe.sample_rate == original_probe.sample_rate
    assert output_probe.duration_sec == original_probe.duration_sec
    assert not np.array_equal(_read_pcm16(source), _read_pcm16(output))


def test_amp_distortion_changes_audio_and_stays_pcm16(tmp_path: Path):
    source = tmp_path / "clean.wav"
    output = tmp_path / "distorted.wav"
    samples = _sine(1000, amplitude=12000)
    _write_pcm16(source, samples)

    apply_audio_transform(
        source,
        output,
        "amp_distortion",
        {"distortion_type": "max_distortion", "rate": 1.0, "max_db": -1.0, "seed": 7},
    )

    distorted = _read_pcm16(output)
    assert not np.array_equal(_read_pcm16(source), distorted)
    assert distorted.min() >= -32768
    assert distorted.max() <= 32767


def test_amp_poly_distortion_changes_audio(tmp_path: Path):
    source = tmp_path / "clean_poly.wav"
    output = tmp_path / "distorted_poly.wav"
    samples = _sine(900, amplitude=12000)
    _write_pcm16(source, samples)

    apply_audio_transform(
        source,
        output,
        "amp_distortion",
        {"distortion_type": "poly_distortion", "rate": 1.0, "a": 1.0, "m": 1, "n": 1, "seed": 8},
    )

    assert not np.array_equal(_read_pcm16(source), _read_pcm16(output))


def test_spectral_mask_is_deterministic_with_seed_and_changes_audio(tmp_path: Path):
    source = tmp_path / "spectral.wav"
    first = tmp_path / "spectral_first.wav"
    second = tmp_path / "spectral_second.wav"
    samples = _sine(500) + _sine(3000)
    _write_pcm16(source, samples)

    params = {"seed": 99}
    apply_audio_transform(source, first, "spectral_mask", params)
    apply_audio_transform(source, second, "spectral_mask", params)

    assert first.read_bytes() == second.read_bytes()
    assert not np.array_equal(_read_pcm16(source), _read_pcm16(first))


def test_signal_mimic_is_deterministic_with_seed(tmp_path: Path):
    source = tmp_path / "input.wav"
    first = tmp_path / "mimic_first.wav"
    second = tmp_path / "mimic_second.wav"
    samples = _sine(450) + _sine(2500) + _sine(5400)
    _write_pcm16(source, samples)

    params = {"seed": 20260620}
    apply_audio_transform(source, first, "signal_mimic", params)
    apply_audio_transform(source, second, "signal_mimic", params)

    assert first.read_bytes() == second.read_bytes()
    assert not np.array_equal(_read_pcm16(source), _read_pcm16(first))
