from __future__ import annotations

SAMPLE_TYPES = ["wake_positive", "similar_negative", "partial_wake", "ordinary_negative"]
VOICE_SOURCES = ["human", "synthetic", "unknown"]
GENDERS = ["male", "female", "unknown"]
AGE_GROUPS = ["child", "teen", "adult", "elderly", "unknown"]
VOLUMES = ["low", "normal", "high", "unknown"]
PITCHES = ["low", "normal", "high", "unknown"]
SPEEDS = ["slow", "normal", "fast", "unknown"]
NOISE_SCENES = ["clean", "home", "office", "car", "street", "music", "babble", "other", "unknown"]
IMPAIRMENT_TYPES = ["none", "device_denoise", "network_denoise", "codec", "far_field", "clipping", "other", "unknown"]
QUALITY_STATUSES = ["draft", "ready", "deprecated"]
VARIANT_KINDS = ["original", "speed_change", "pitch_shift", "volume_gain", "noise_mix", "device_denoise", "network_denoise", "codec", "far_field", "clipping", "combined", "other"]


def as_dict() -> dict[str, list[str]]:
    return {
        "sample_type": SAMPLE_TYPES,
        "voice_source": VOICE_SOURCES,
        "gender": GENDERS,
        "age_group": AGE_GROUPS,
        "volume": VOLUMES,
        "pitch": PITCHES,
        "speed": SPEEDS,
        "noise_scene": NOISE_SCENES,
        "impairment_type": IMPAIRMENT_TYPES,
        "quality_status": QUALITY_STATUSES,
        "variant_kind": VARIANT_KINDS,
    }
