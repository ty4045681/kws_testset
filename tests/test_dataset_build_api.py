from sqlmodel import Session, select

from kws_testset.models.audio import AudioSource, AudioVariant
from kws_testset.models.dataset import DatasetItem, DatasetVersion


def insert_ready_variant(client, variant_id: str, sample_type: str = "wake_positive", speaker_id: str | None = None) -> None:
    with Session(client.app.state.engine) as session:
        source = AudioSource(
            id=f"src_{variant_id}",
            original_filename=f"{variant_id}.wav",
            stored_path=f"/tmp/{variant_id}.wav",
            sha256=f"sha_source_{variant_id}",
            duration_sec=1.0,
            sample_rate=16000,
            channels=1,
            bit_depth=16,
        )
        variant = AudioVariant(
            id=variant_id,
            source_id=source.id,
            variant_kind="original",
            stored_path=source.stored_path,
            sha256=f"sha_variant_{variant_id}",
            duration_sec=1.0,
            sample_rate=16000,
            channels=1,
            text="你好小智" if sample_type == "wake_positive" else "你好小志",
            normalized_text="你好小智" if sample_type == "wake_positive" else "你好小志",
            sample_type=sample_type,
            quality_status="ready",
            voice_source="human",
            speaker_id=speaker_id,
            gender="female",
            age_group="adult",
            volume="normal",
            pitch="normal",
            speed="normal",
            noise_scene="clean",
            impairment_type="none",
        )
        session.add(source)
        session.add(variant)
        session.commit()


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


def test_build_version_after_deleted_middle_version_uses_next_max_version(client):
    insert_ready_variant(client, "var_version_anchor")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "version_gap_regression",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    spec_id = spec_response.json()["id"]
    versions = [client.post(f"/api/dataset-specs/{spec_id}/build").json() for _ in range(3)]

    with Session(client.app.state.engine) as session:
        for item in session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == versions[1]["id"])).all():
            session.delete(item)
        version_to_delete = session.get(DatasetVersion, versions[1]["id"])
        session.delete(version_to_delete)
        session.commit()

    response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert response.status_code == 200
    assert response.json()["version"] == 4


def test_build_selection_is_stable_by_variant_id_not_insert_order(client):
    for variant_id in ["var_c", "var_b", "var_a"]:
        insert_ready_variant(client, variant_id)
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "deterministic_seed_regression",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    build_response = client.post(f"/api/dataset-specs/{spec_response.json()['id']}/build")

    assert build_response.status_code == 200
    with Session(client.app.state.engine) as session:
        item = session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == build_response.json()["id"])).one()
        assert item.variant_id == "var_c"


def test_create_spec_rejects_unknown_filter_key(client):
    response = client.post(
        "/api/dataset-specs",
        json={
            "name": "bad_filter_key",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"noise_scenes": ["clean"]},
            "balance_by": [],
        },
    )

    assert response.status_code == 400
    assert "unknown filter field" in response.json()["detail"]


def test_balance_by_speaker_id_uses_candidate_metadata(client):
    insert_ready_variant(client, "var_a1", speaker_id="speaker_a")
    insert_ready_variant(client, "var_a2", speaker_id="speaker_a")
    insert_ready_variant(client, "var_b1", speaker_id="speaker_b")
    insert_ready_variant(client, "var_b2", speaker_id="speaker_b")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "speaker_balance_regression",
            "target_keyword": "你好小智",
            "sampling_seed": 5,
            "quotas": {"wake_positive": 2},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["speaker_id"],
        },
    )

    build_response = client.post(f"/api/dataset-specs/{spec_response.json()['id']}/build")

    assert build_response.status_code == 200
    assert build_response.json()["coverage_summary"]["by_field"]["speaker_id"] == {"speaker_a": 1, "speaker_b": 1}


def test_manual_include_of_draft_variant_is_rejected(client):
    insert_ready_variant(client, "var_draft_include")
    with Session(client.app.state.engine) as session:
        variant = session.get(AudioVariant, "var_draft_include")
        variant.quality_status = "draft"
        session.add(variant)
        session.commit()
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "draft_include_regression",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    spec_id = spec_response.json()["id"]
    client.post(
        f"/api/dataset-specs/{spec_id}/overrides",
        json={"variant_id": "var_draft_include", "action": "include", "reason": "draft anchor"},
    )

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 400
    assert "manual include variant must be ready" in build_response.json()["detail"]


def test_manual_include_sample_type_outside_quota_is_rejected(client):
    insert_ready_variant(client, "var_negative_include", sample_type="similar_negative")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "quota_mismatch_include_regression",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    spec_id = spec_response.json()["id"]
    client.post(
        f"/api/dataset-specs/{spec_id}/overrides",
        json={"variant_id": "var_negative_include", "action": "include", "reason": "wrong type"},
    )

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 400
    assert "manual include sample_type must be in quotas" in build_response.json()["detail"]


def test_manual_includes_exceeding_quota_are_rejected(client):
    insert_ready_variant(client, "var_include_1")
    insert_ready_variant(client, "var_include_2")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "include_over_quota_regression",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    spec_id = spec_response.json()["id"]
    for variant_id in ["var_include_1", "var_include_2"]:
        client.post(
            f"/api/dataset-specs/{spec_id}/overrides",
            json={"variant_id": variant_id, "action": "include", "reason": "anchor"},
        )

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 400
    assert "manual includes exceed quota" in build_response.json()["detail"]


def test_re_export_uses_a_fresh_directory(client, wav_factory):
    import_asset(client, wav_factory, "reexport_pos.wav", "你好小智", "wake_positive")
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "reexport_regression",
            "target_keyword": "你好小智",
            "quotas": {"wake_positive": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": [],
        },
    )
    version = client.post(f"/api/dataset-specs/{spec_response.json()['id']}/build").json()

    first_export = client.post(f"/api/dataset-versions/{version['id']}/export").json()
    second_export = client.post(f"/api/dataset-versions/{version['id']}/export").json()

    assert first_export["export_dir"] != second_export["export_dir"]
