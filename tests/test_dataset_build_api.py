def import_asset(client, wav_factory, name, text, sample_type):
    wav_path = wav_factory(name)
    response = client.post(
        "/api/imports",
        json={
            "name": f"batch_{name}",
            "files": [
                {
                    "path": str(wav_path),
                    "text": text,
                    "sample_type": sample_type,
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


def test_create_spec_and_build_version(client, wav_factory):
    import_asset(client, wav_factory, "pos.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "neg.wav", "你好小志", "similar_negative")

    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "wakeword_regression",
            "description": "main regression set",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 1, "similar_negative": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["gender", "noise_scene"],
            "min_duration_sec": 0.01,
            "max_duration_sec": 5.0,
        },
    )
    assert spec_response.status_code == 200
    spec_id = spec_response.json()["id"]

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 200
    payload = build_response.json()
    assert payload["item_count"] == 2
    assert payload["version"] == 1
    assert payload["coverage_summary"]["total"] == 2

from sqlmodel import Session, select

from kws_testset.models.dataset import DatasetVersion


def test_manual_include_bypasses_filters_and_is_snapshotted(client, wav_factory):
    import_asset(client, wav_factory, "pos_clean.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "pos_car.wav", "你好小智", "wake_positive")
    assets = client.get("/api/assets").json()["items"]
    # The second imported asset is deterministic enough for this minimum API test because assets are ordered by created_at.
    car_variant_id = assets[-1]["id"]

    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "manual_include_regression",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 1},
            "filters": {"noise_scene": ["street"]},
            "balance_by": ["noise_scene"],
        },
    )
    spec_id = spec_response.json()["id"]
    override_response = client.post(
        f"/api/dataset-specs/{spec_id}/overrides",
        json={"variant_id": car_variant_id, "action": "include", "reason": "anchor outside filter"},
    )
    assert override_response.status_code == 200

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 200
    payload = build_response.json()
    assert payload["item_count"] == 1
    assert payload["coverage_summary"]["by_field"]["noise_scene"] == {"clean": 1}

    with Session(client.app.state.engine) as session:
        version = session.get(DatasetVersion, payload["id"])
        assert version is not None
        assert version.rules_snapshot["overrides"] == [
            {"variant_id": car_variant_id, "action": "include", "reason": "anchor outside filter"}
        ]
        assert version.rules_snapshot["target_keyword"] == "你好小智"


def test_duplicate_dataset_names_build_with_unique_version_ids(client, wav_factory):
    import_asset(client, wav_factory, "dup_pos.wav", "你好小智", "wake_positive")

    spec_ids = []
    for _ in range(2):
        response = client.post(
            "/api/dataset-specs",
            json={
                "name": "same_name",
                "target_keyword": "你好小智",
                "quotas": {"wake_positive": 1},
                "filters": {"quality_status": ["ready"]},
                "balance_by": ["gender"],
            },
        )
        assert response.status_code == 200
        spec_ids.append(response.json()["id"])

    first = client.post(f"/api/dataset-specs/{spec_ids[0]}/build")
    second = client.post(f"/api/dataset-specs/{spec_ids[1]}/build")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]


def test_export_path_uses_safe_dataset_slug(client, wav_factory):
    import_asset(client, wav_factory, "slug_pos.wav", "你好小智", "wake_positive")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "../bad:name*dataset",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["gender"],
        },
    )
    version = client.post(f"/api/dataset-specs/{spec_response.json()['id']}/build").json()

    export_response = client.post(f"/api/dataset-versions/{version['id']}/export")

    assert export_response.status_code == 200
    export_dir = export_response.json()["export_dir"]
    assert ".." not in export_dir
    assert "bad_name_dataset" in export_dir
