import math
from pathlib import Path
import struct
import wave

from sqlmodel import Session

from kws_testset.models.audio import AudioVariant


def _import_ready_path(client, wav_path: Path, name: str) -> dict:
    before = {item["id"] for item in client.get("/api/assets").json()["items"]}
    response = client.post(
        "/api/imports",
        json={
            "name": f"transform_batch_{name}",
            "files": [
                {
                    "path": str(wav_path),
                    "text": "你好小智",
                    "sample_type": "wake_positive",
                    "quality_status": "ready",
                    "voice_source": "human",
                    "gender": "female",
                    "age_group": "adult",
                    "volume": "normal",
                    "pitch": "normal",
                    "speed": "normal",
                    "noise_scene": "clean",
                    "impairment_type": "none",
                }
            ],
        },
    )
    assert response.status_code == 200
    assets = client.get("/api/assets").json()["items"]
    created = [item for item in assets if item["id"] not in before]
    assert len(created) == 1
    return created[0]


def _import_ready_asset(client, wav_factory, name: str = "transform_input.wav") -> dict:
    return _import_ready_path(client, wav_factory(name), name)


def _write_mixed_sine_wav(path: Path, seconds: float = 0.15) -> Path:
    sample_rate = 16000
    frames = int(sample_rate * seconds)
    samples = []
    for frame in range(frames):
        t = frame / sample_rate
        value = 9000 * math.sin(2 * math.pi * 700 * t) + 5000 * math.sin(2 * math.pi * 5200 * t)
        samples.append(max(-32768, min(32767, int(round(value)))))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def test_create_transform_job_rejects_unknown_transform_kind(client, wav_factory):
    asset = _import_ready_asset(client, wav_factory, "unknown_transform.wav")

    response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [asset["id"]], "transform_kind": "not_real", "params": {}},
    )

    assert response.status_code == 400
    assert "unknown transform_kind" in response.json()["detail"]


def test_volume_gain_transform_creates_draft_child_variant_with_lineage(client, wav_factory):
    parent = _import_ready_asset(client, wav_factory, "volume_gain_parent.wav")

    response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [parent["id"]], "transform_kind": "volume_gain", "params": {"gain_db": 6.0}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["requested_count"] == 1
    assert payload["created_count"] == 1
    assert payload["failed_count"] == 0
    assert len(payload["created_variant_ids"]) == 1
    assert payload["results"] == [
        {
            "input_variant_id": parent["id"],
            "status": "created",
            "created_variant_id": payload["created_variant_ids"][0],
            "errors": [],
        }
    ]

    child_id = payload["created_variant_ids"][0]
    with Session(client.app.state.engine) as session:
        parent_row = session.get(AudioVariant, parent["id"])
        child = session.get(AudioVariant, child_id)

    assert parent_row is not None
    assert child is not None
    assert child.parent_variant_id == parent["id"]
    assert child.source_id == parent_row.source_id
    assert child.variant_kind == "volume_gain"
    assert child.quality_status == "draft"
    assert child.text == parent_row.text
    assert child.sha256 != parent_row.sha256
    assert child.processing_params == {"transform_kind": "volume_gain", "params": {"gain_db": 6.0}}
    assert child.impairment_chain[-1] == {"transform_kind": "volume_gain", "params": {"gain_db": 6.0}}
    assert Path(child.stored_path).exists()
    assert "library" in Path(child.stored_path).parts
    assert "variants" in Path(child.stored_path).parts


def test_transform_jobs_can_be_listed_and_fetched(client, wav_factory):
    asset = _import_ready_asset(client, wav_factory, "transform_list.wav")
    create_response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [asset["id"]], "transform_kind": "volume_gain", "params": {"gain_db": -3.0}},
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["id"]

    list_response = client.get("/api/transform-jobs")
    detail_response = client.get(f"/api/transform-jobs/{job_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == job_id
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == job_id
    assert detail_response.json()["created_count"] == 1


def test_transform_job_reports_missing_variants_per_row(client, wav_factory):
    asset = _import_ready_asset(client, wav_factory, "transform_partial.wav")

    response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [asset["id"], "missing_variant"], "transform_kind": "volume_gain", "params": {"gain_db": 3.0}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["requested_count"] == 2
    assert payload["created_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["results"][0]["status"] == "created"
    assert payload["results"][1] == {
        "input_variant_id": "missing_variant",
        "status": "error",
        "created_variant_id": None,
        "errors": ["variant not found"],
    }


def test_narrowband_transform_creates_draft_child_variant_with_lineage(client, tmp_path):
    parent = _import_ready_path(client, _write_mixed_sine_wav(tmp_path / "narrowband_parent.wav"), "narrowband_parent.wav")

    response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [parent["id"]], "transform_kind": "narrowband", "params": {"target_sample_rate": 8000}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["created_count"] == 1
    assert payload["failed_count"] == 0

    child_id = payload["created_variant_ids"][0]
    with Session(client.app.state.engine) as session:
        parent_row = session.get(AudioVariant, parent["id"])
        child = session.get(AudioVariant, child_id)

    assert parent_row is not None
    assert child is not None
    assert child.parent_variant_id == parent["id"]
    assert child.variant_kind == "codec"
    assert child.impairment_type == "codec"
    assert child.quality_status == "draft"
    assert child.sample_rate == parent_row.sample_rate
    assert child.sha256 != parent_row.sha256
    assert child.processing_params == {"transform_kind": "narrowband", "params": {"target_sample_rate": 8000}}
    assert child.impairment_chain[-1] == {"transform_kind": "narrowband", "params": {"target_sample_rate": 8000}}


def test_amp_distortion_transform_uses_clipping_taxonomy_kind(client, tmp_path):
    parent = _import_ready_path(client, _write_mixed_sine_wav(tmp_path / "clipping_parent.wav"), "clipping_parent.wav")

    response = client.post(
        "/api/transform-jobs",
        json={
            "variant_ids": [parent["id"]],
            "transform_kind": "amp_distortion",
            "params": {"distortion_type": "max_distortion", "rate": 1.0, "max_db": -1.0, "seed": 5},
        },
    )

    assert response.status_code == 200
    child_id = response.json()["created_variant_ids"][0]
    with Session(client.app.state.engine) as session:
        child = session.get(AudioVariant, child_id)

    assert child is not None
    assert child.variant_kind == "clipping"
    assert child.impairment_type == "clipping"
    assert child.processing_params["transform_kind"] == "amp_distortion"


def test_repeated_deterministic_transform_returns_existing_child_without_failure(client, wav_factory):
    parent = _import_ready_asset(client, wav_factory, "repeat_parent.wav")
    payload = {"variant_ids": [parent["id"]], "transform_kind": "volume_gain", "params": {"gain_db": 6.0}}
    first = client.post("/api/transform-jobs", json=payload)
    assert first.status_code == 200
    first_child_id = first.json()["created_variant_ids"][0]

    second = client.post("/api/transform-jobs", json=payload)

    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "completed"
    assert body["created_count"] == 1
    assert body["failed_count"] == 0
    assert body["created_variant_ids"] == [first_child_id]
    assert body["results"] == [
        {
            "input_variant_id": parent["id"],
            "status": "existing",
            "created_variant_id": first_child_id,
            "errors": [],
        }
    ]


def test_null_numeric_transform_param_returns_clear_error(client, wav_factory):
    parent = _import_ready_asset(client, wav_factory, "null_param_parent.wav")

    response = client.post(
        "/api/transform-jobs",
        json={"variant_ids": [parent["id"]], "transform_kind": "volume_gain", "params": {"gain_db": None}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failed_count"] == 1
    assert body["results"][0]["errors"] == ["gain_db must be a finite number"]
