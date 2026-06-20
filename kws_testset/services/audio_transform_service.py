from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Callable
import wave

import numpy as np
from scipy import signal


SUPPORTED_TRANSFORM_KINDS = {
    "volume_gain",
    "speed_change",
    "noise_mix",
    "subband_eq",
    "band_limit",
    "narrowband",
    "spectral_mask",
    "amp_distortion",
    "signal_mimic",
}

PCM16_MIN = -32768
PCM16_MAX = 32767


@dataclass(frozen=True)
class Pcm16Wav:
    channels: int
    sample_rate: int
    samples: np.ndarray


def _clamp_pcm16(samples: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(samples), PCM16_MIN, PCM16_MAX)


def _read_pcm16(path: Path) -> Pcm16Wav:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if sample_width != 2:
        raise ValueError(f"only 16-bit PCM WAV files are supported, got sample_width={sample_width}")
    if channels <= 0:
        raise ValueError(f"invalid channel count: {channels}")
    if sample_rate <= 0:
        raise ValueError(f"invalid sample_rate: {sample_rate}")

    raw = np.frombuffer(frames, dtype="<i2").astype(np.float64)
    if raw.size % channels != 0:
        raise ValueError("PCM frame data is not aligned to channel count")
    samples = raw.reshape((-1, channels)) if raw.size else np.empty((0, channels), dtype=np.float64)
    return Pcm16Wav(channels=channels, sample_rate=sample_rate, samples=samples)


def _write_pcm16(path: Path, wav_data: Pcm16Wav) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = _clamp_pcm16(wav_data.samples).astype("<i2").reshape(-1).tobytes()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(wav_data.channels)
        wav.setsampwidth(2)
        wav.setframerate(wav_data.sample_rate)
        wav.writeframes(frames)


def _require_range(name: str, value: float, minimum: float, maximum: float) -> float:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


def _rng_from_params(params: dict[str, Any]) -> np.random.Generator:
    return np.random.default_rng(int(params.get("seed", 0)))


def _match_length(samples: np.ndarray, frame_count: int) -> np.ndarray:
    if samples.shape[0] == frame_count:
        return samples
    if samples.shape[0] > frame_count:
        return samples[:frame_count]
    if samples.shape[0] == 0:
        return np.zeros(frame_count, dtype=np.float64)
    return np.pad(samples, (0, frame_count - samples.shape[0]), mode="edge")


def _apply_channelwise(wav_data: Pcm16Wav, transform: Callable[[np.ndarray], np.ndarray]) -> Pcm16Wav:
    if wav_data.samples.size == 0:
        return wav_data
    output = [
        _match_length(np.asarray(transform(wav_data.samples[:, channel]), dtype=np.float64), wav_data.samples.shape[0])
        for channel in range(wav_data.channels)
    ]
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=np.column_stack(output))


def _volume_gain(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    gain_db = _require_range("gain_db", float(params.get("gain_db", 0.0)), -30.0, 30.0)
    if gain_db == 0.0:
        raise ValueError("gain_db must not be 0 for a generated variant")
    factor = math.pow(10.0, gain_db / 20.0)
    return Pcm16Wav(
        channels=wav_data.channels,
        sample_rate=wav_data.sample_rate,
        samples=wav_data.samples * factor,
    )


def _speed_change(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    speed_factor = _require_range("speed_factor", float(params.get("speed_factor", 1.0)), 0.5, 2.0)
    if speed_factor == 1.0:
        raise ValueError("speed_factor must not be 1 for a generated variant")
    if wav_data.samples.size == 0:
        return wav_data

    frame_count = wav_data.samples.shape[0]
    output_frame_count = max(1, int(round(frame_count / speed_factor)))
    source_positions = np.arange(frame_count, dtype=np.float64)
    output_positions = np.clip(np.arange(output_frame_count, dtype=np.float64) * speed_factor, 0, frame_count - 1)
    output = [
        np.interp(output_positions, source_positions, wav_data.samples[:, channel])
        for channel in range(wav_data.channels)
    ]
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=np.column_stack(output))


def _noise_mix(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    snr_db = _require_range("snr_db", float(params.get("snr_db", 20.0)), -5.0, 40.0)
    if wav_data.samples.size == 0:
        return wav_data
    rng = _rng_from_params(params)
    signal_rms = float(np.sqrt(np.mean(np.square(wav_data.samples))))
    noise_rms = signal_rms / math.pow(10.0, snr_db / 20.0) if signal_rms > 0 else 100.0
    noise = rng.normal(0.0, noise_rms, size=wav_data.samples.shape)
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=wav_data.samples + noise)


def _stft_params(samples: np.ndarray) -> tuple[int, int, int]:
    nfft = 512
    nperseg = min(480, max(16, samples.shape[0]))
    hop = min(160, max(1, nperseg // 2))
    noverlap = nperseg - hop
    return nfft, nperseg, noverlap


def _stft(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int, int]]:
    nfft, nperseg, noverlap = _stft_params(samples)
    freqs, times, spectrum = signal.stft(
        samples,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        boundary="zeros",
        padded=True,
    )
    return freqs, times, spectrum, (nfft, nperseg, noverlap)


def _istft(spectrum: np.ndarray, sample_rate: int, params: tuple[int, int, int], frame_count: int) -> np.ndarray:
    nfft, nperseg, noverlap = params
    _, output = signal.istft(
        spectrum,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        input_onesided=True,
        boundary=True,
    )
    return _match_length(np.asarray(output, dtype=np.float64), frame_count)


def _generate_subband_bins(rng: np.random.Generator, bin_count: int) -> list[int]:
    boundaries = [0, 1]
    for index in range(2, 11):
        if index < 4:
            step = int(rng.integers(1, 3))
        elif index < 7:
            step = int(rng.integers(8, 10))
        elif index < 10:
            step = int(rng.integers(32, 64))
        else:
            step = bin_count
        boundaries.append(min(bin_count, boundaries[-1] + step))
    boundaries[-1] = bin_count
    deduped: list[int] = []
    for boundary in boundaries:
        if not deduped or boundary > deduped[-1]:
            deduped.append(boundary)
    if deduped[-1] != bin_count:
        deduped.append(bin_count)
    return deduped


def _subband_eq(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    rng = _rng_from_params(params)
    low_min_db = float(params.get("low_min_gain_db", -10.0))
    high_min_db = float(params.get("high_min_gain_db", -20.0))

    def transform(channel: np.ndarray) -> np.ndarray:
        freqs, _, spectrum, stft_params = _stft(channel, wav_data.sample_rate)
        boundaries = _generate_subband_bins(rng, len(freqs))
        gains = np.ones(len(freqs), dtype=np.float64)
        for band_index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
            min_db = high_min_db if band_index >= len(boundaries) - 4 else low_min_db
            gain_db = float(rng.uniform(min_db, 0.0))
            gains[start:end] = math.pow(10.0, gain_db / 20.0)
        return _istft(spectrum * gains[:, None], wav_data.sample_rate, stft_params, channel.shape[0])

    return _apply_channelwise(wav_data, transform)


def _lowpass_fft(channel: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    spectrum = np.fft.rfft(channel)
    freqs = np.fft.rfftfreq(channel.shape[0], d=1.0 / sample_rate)
    spectrum[freqs > cutoff_hz] = 0
    return np.fft.irfft(spectrum, n=channel.shape[0])


def _resample_to_rate(channel: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    down_gcd = math.gcd(source_rate, target_rate)
    downsampled = signal.resample_poly(channel, target_rate // down_gcd, source_rate // down_gcd)
    up_gcd = math.gcd(target_rate, source_rate)
    restored = signal.resample_poly(downsampled, source_rate // up_gcd, target_rate // up_gcd)
    return _match_length(np.asarray(restored, dtype=np.float64), channel.shape[0])


def _band_limit(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    mode = str(params.get("mode", params.get("limit", "freq")))
    nyquist = wav_data.sample_rate / 2
    cutoff_hz = _require_range("cutoff_hz", float(params.get("cutoff_hz", min(4000.0, nyquist - 1))), 20.0, nyquist - 1)

    if mode == "freq":
        return _apply_channelwise(wav_data, lambda channel: _lowpass_fft(channel, wav_data.sample_rate, cutoff_hz))

    if mode == "iir":
        order = int(_require_range("filter_order", float(params.get("filter_order", 6)), 1, 12))
        sos = signal.butter(order, cutoff_hz / nyquist, btype="lowpass", output="sos")

        def transform(channel: np.ndarray) -> np.ndarray:
            if channel.shape[0] > order * 6:
                return signal.sosfiltfilt(sos, channel)
            return signal.sosfilt(sos, channel)

        return _apply_channelwise(wav_data, transform)

    if mode == "resample":
        target_rate = int(params.get("target_sample_rate", max(1000, min(wav_data.sample_rate - 1, int(cutoff_hz * 2)))))
        if not 1000 <= target_rate < wav_data.sample_rate:
            raise ValueError("target_sample_rate must be lower than the source sample rate")
        return _apply_channelwise(wav_data, lambda channel: _resample_to_rate(channel, wav_data.sample_rate, target_rate))

    raise ValueError("mode must be one of: freq, iir, resample")


def _narrowband(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    target_rate = int(params.get("target_sample_rate", 8000))
    if not 1000 <= target_rate < wav_data.sample_rate:
        raise ValueError("target_sample_rate must be lower than the source sample rate")
    return _apply_channelwise(wav_data, lambda channel: _resample_to_rate(channel, wav_data.sample_rate, target_rate))


def _spectral_mask(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    rng = _rng_from_params(params)
    frequency_masks = int(_require_range("frequency_masks", float(params.get("frequency_masks", 2)), 1, 8))
    time_masks = int(_require_range("time_masks", float(params.get("time_masks", 1)), 0, 8))
    min_gain = _require_range("min_gain", float(params.get("min_gain", 0.05)), 0.0, 1.0)
    max_gain = _require_range("max_gain", float(params.get("max_gain", 0.6)), min_gain, 1.0)

    def transform(channel: np.ndarray) -> np.ndarray:
        freqs, times, spectrum, stft_params = _stft(channel, wav_data.sample_rate)
        mask = np.ones(spectrum.shape, dtype=np.float64)
        for _ in range(frequency_masks):
            width = int(rng.integers(max(1, len(freqs) // 24), max(2, len(freqs) // 5)))
            start = int(rng.integers(0, max(1, len(freqs) - width + 1)))
            mask[start : start + width, :] *= float(rng.uniform(min_gain, max_gain))
        for _ in range(time_masks):
            width = int(rng.integers(1, max(2, len(times) // 4 + 1)))
            start = int(rng.integers(0, max(1, len(times) - width + 1)))
            mask[:, start : start + width] *= float(rng.uniform(min_gain, max_gain))
        return _istft(spectrum * mask, wav_data.sample_rate, stft_params, channel.shape[0])

    return _apply_channelwise(wav_data, transform)


def _db2amp(db: float) -> float:
    return math.pow(10.0, db / 20.0)


def _amp2db(amp: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(amp, 1e-12))


def _generate_amp_masks(rng: np.random.Generator, mask_number: int) -> list[tuple[float, float]]:
    if mask_number <= 0:
        return [(_db2amp(left), _db2amp(right)) for left, right in [(-110, -95), (-90, -80), (-65, -60), (-50, -30), (-15, 0)]]
    steps = np.concatenate(([0.0], np.cumsum(rng.uniform(0.5, 1.0, size=(2 * mask_number) - 1))))
    maximum = float(steps[-1])
    masks: list[tuple[float, float]] = []
    for index in range(mask_number):
        left_db = ((float(steps[2 * index]) - maximum) / maximum) * 100.0
        right_db = ((float(steps[(2 * index) + 1]) - maximum) / maximum) * 100.0
        masks.append((_db2amp(left_db), _db2amp(right_db)))
    return masks


def _inside_amp_masks(abs_samples: np.ndarray, masks: list[tuple[float, float]]) -> np.ndarray:
    included = np.zeros(abs_samples.shape, dtype=bool)
    for left, right in masks:
        included |= (abs_samples >= left) & (abs_samples <= right)
    return included


def _poly_distortion(normalized: np.ndarray, a: float, m: int, n: int) -> np.ndarray:
    abs_samples = np.abs(normalized)
    db_norm = np.clip((_amp2db(abs_samples) / 100.0) + 1.0, 0.0, 1.0)
    shaped = np.clip(a * np.power(db_norm, m) * np.power(1.0 - db_norm, n) + db_norm, 0.0, 1.0)
    amp = np.minimum(0.9997, np.power(10.0, ((shaped - 1.0) * 100.0) / 20.0))
    return np.where(abs_samples < 1e-6, 0.0, np.sign(normalized) * amp)


def _amp_distortion(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    distortion_type = str(params.get("distortion_type", "max_distortion"))
    rate = _require_range("rate", float(params.get("rate", 0.8)), 0.0, 1.0)
    rng = _rng_from_params(params)
    normalized = np.clip(wav_data.samples / PCM16_MAX, -1.0, 1.0)
    mutate = rng.random(normalized.shape) < rate

    if distortion_type == "gain_db":
        gain_db = _require_range("gain_db", float(params.get("gain_db", 6.0)), -30.0, 30.0)
        transformed = np.clip(normalized * _db2amp(gain_db), -0.997, 0.997)
    elif distortion_type == "max_distortion":
        max_amp = min(0.997, _db2amp(float(params.get("max_db", -0.03))))
        transformed = np.sign(normalized) * max_amp
    elif distortion_type in {"fence_distortion", "jag_distortion"}:
        mask_number = int(_require_range("mask_number", float(params.get("mask_number", 4)), 0, 12))
        positive_mask = _generate_amp_masks(rng, mask_number)
        negative_mask = _generate_amp_masks(rng, mask_number)
        abs_samples = np.abs(normalized)
        included = np.where(
            normalized >= 0,
            _inside_amp_masks(abs_samples, positive_mask),
            _inside_amp_masks(abs_samples, negative_mask),
        )
        if distortion_type == "fence_distortion":
            max_amp = min(0.997, _db2amp(float(params.get("max_db", -0.03))))
            transformed = np.where(included, np.sign(normalized) * max_amp, 0.0)
        else:
            transformed = np.where(included, normalized, 0.0)
    elif distortion_type in {"poly_distortion", "quad_distortion"}:
        if distortion_type == "quad_distortion":
            a, m, n = 1.0, 1, 1
        else:
            a = float(params.get("a", 1.0))
            m = int(_require_range("m", float(params.get("m", 1)), 1, 8))
            n = int(_require_range("n", float(params.get("n", 1)), 1, 8))
        transformed = _poly_distortion(normalized, a, m, n)
    else:
        raise ValueError(
            "distortion_type must be one of: gain_db, max_distortion, fence_distortion, "
            "jag_distortion, poly_distortion, quad_distortion"
        )

    output = np.where(mutate, transformed, normalized)
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=output * PCM16_MAX)


def _signal_mimic(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    rng = _rng_from_params(params)
    output = wav_data
    applied = False

    def child_seed() -> int:
        return int(rng.integers(0, 2**31 - 1))

    if rng.random() < float(params.get("subband_probability", 0.4)):
        output = _subband_eq(output, {"seed": child_seed()})
        applied = True

    if output.samples.size and rng.random() < float(params.get("mute_probability", 0.1)):
        samples = output.samples.copy()
        frame_count = samples.shape[0]
        start = int(rng.integers(0, max(1, frame_count // 2)))
        length = int(rng.integers(max(1, frame_count // 20), max(2, frame_count // 4)))
        samples[start : min(frame_count, start + length), :] = 0
        output = Pcm16Wav(channels=output.channels, sample_rate=output.sample_rate, samples=samples)
        applied = True

    if rng.random() < float(params.get("band_limit_probability", 0.5)):
        cutoff_max = max(1200, min(int(output.sample_rate / 2) - 1, 4500))
        cutoff_min = min(3000, cutoff_max)
        cutoff_hz = int(rng.integers(cutoff_min, cutoff_max + 1))
        output = _band_limit(output, {"mode": "freq", "cutoff_hz": cutoff_hz})
        applied = True

    if rng.random() < float(params.get("spectral_mask_probability", 0.1)):
        output = _spectral_mask(output, {"seed": child_seed()})
        applied = True

    if rng.random() < float(params.get("narrowband_probability", 0.2)) and output.sample_rate > 8000:
        output = _narrowband(output, {"target_sample_rate": 8000})
        applied = True

    if not applied:
        output = _subband_eq(output, {"seed": child_seed()})

    return output


def apply_audio_transform(source_path: Path, output_path: Path, transform_kind: str, params: dict[str, Any]) -> None:
    if transform_kind not in SUPPORTED_TRANSFORM_KINDS:
        raise ValueError(f"unknown transform_kind: {transform_kind}")
    wav_data = _read_pcm16(source_path)
    transforms: dict[str, Callable[[Pcm16Wav, dict[str, Any]], Pcm16Wav]] = {
        "volume_gain": _volume_gain,
        "speed_change": _speed_change,
        "noise_mix": _noise_mix,
        "subband_eq": _subband_eq,
        "band_limit": _band_limit,
        "narrowband": _narrowband,
        "spectral_mask": _spectral_mask,
        "amp_distortion": _amp_distortion,
        "signal_mimic": _signal_mimic,
    }
    transformed = transforms[transform_kind](wav_data, params)
    _write_pcm16(output_path, transformed)
