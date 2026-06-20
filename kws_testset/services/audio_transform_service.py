from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
import struct
from typing import Any
import wave


SUPPORTED_TRANSFORM_KINDS = {"volume_gain", "speed_change", "noise_mix"}


@dataclass(frozen=True)
class Pcm16Wav:
    channels: int
    sample_rate: int
    samples: list[int]


def _clamp_pcm16(value: float) -> int:
    return max(-32768, min(32767, int(round(value))))


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
    sample_count = len(frames) // 2
    samples = list(struct.unpack(f"<{sample_count}h", frames)) if sample_count else []
    return Pcm16Wav(channels=channels, sample_rate=sample_rate, samples=samples)


def _write_pcm16(path: Path, wav_data: Pcm16Wav) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = struct.pack(f"<{len(wav_data.samples)}h", *wav_data.samples) if wav_data.samples else b""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(wav_data.channels)
        wav.setsampwidth(2)
        wav.setframerate(wav_data.sample_rate)
        wav.writeframes(frames)


def _volume_gain(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    gain_db = float(params.get("gain_db", 0.0))
    if not -30.0 <= gain_db <= 30.0:
        raise ValueError("gain_db must be between -30 and 30")
    if gain_db == 0.0:
        raise ValueError("gain_db must not be 0 for a generated variant")
    factor = math.pow(10.0, gain_db / 20.0)
    return Pcm16Wav(
        channels=wav_data.channels,
        sample_rate=wav_data.sample_rate,
        samples=[_clamp_pcm16(sample * factor) for sample in wav_data.samples],
    )


def _frame_at(frames: list[tuple[int, ...]], position: float, channels: int) -> tuple[int, ...]:
    low_index = int(math.floor(position))
    high_index = min(low_index + 1, len(frames) - 1)
    ratio = position - low_index
    low = frames[min(low_index, len(frames) - 1)]
    high = frames[high_index]
    return tuple(_clamp_pcm16(low[channel] * (1.0 - ratio) + high[channel] * ratio) for channel in range(channels))


def _speed_change(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    speed_factor = float(params.get("speed_factor", 1.0))
    if not 0.5 <= speed_factor <= 2.0:
        raise ValueError("speed_factor must be between 0.5 and 2.0")
    if speed_factor == 1.0:
        raise ValueError("speed_factor must not be 1 for a generated variant")
    if not wav_data.samples:
        return wav_data
    frames = [
        tuple(wav_data.samples[index : index + wav_data.channels])
        for index in range(0, len(wav_data.samples), wav_data.channels)
    ]
    output_frame_count = max(1, int(round(len(frames) / speed_factor)))
    output_samples: list[int] = []
    for frame_index in range(output_frame_count):
        position = min(frame_index * speed_factor, len(frames) - 1)
        output_samples.extend(_frame_at(frames, position, wav_data.channels))
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=output_samples)


def _noise_mix(wav_data: Pcm16Wav, params: dict[str, Any]) -> Pcm16Wav:
    snr_db = float(params.get("snr_db", 20.0))
    if not -5.0 <= snr_db <= 40.0:
        raise ValueError("snr_db must be between -5 and 40")
    seed = int(params.get("seed", 0))
    rng = random.Random(seed)
    if not wav_data.samples:
        return wav_data
    signal_rms = math.sqrt(sum(sample * sample for sample in wav_data.samples) / len(wav_data.samples))
    noise_rms = signal_rms / math.pow(10.0, snr_db / 20.0) if signal_rms > 0 else 100.0
    output = [_clamp_pcm16(sample + rng.gauss(0.0, noise_rms)) for sample in wav_data.samples]
    return Pcm16Wav(channels=wav_data.channels, sample_rate=wav_data.sample_rate, samples=output)


def apply_audio_transform(source_path: Path, output_path: Path, transform_kind: str, params: dict[str, Any]) -> None:
    if transform_kind not in SUPPORTED_TRANSFORM_KINDS:
        raise ValueError(f"unknown transform_kind: {transform_kind}")
    wav_data = _read_pcm16(source_path)
    if transform_kind == "volume_gain":
        transformed = _volume_gain(wav_data, params)
    elif transform_kind == "speed_change":
        transformed = _speed_change(wav_data, params)
    else:
        transformed = _noise_mix(wav_data, params)
    _write_pcm16(output_path, transformed)
