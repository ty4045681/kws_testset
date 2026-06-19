from tests.test_dataset_build_api import import_asset


def _create_spec(client):
    response = client.post(
        "/api/dataset-specs",
        json={
            "name": "browse_spec",
            "description": "browse api spec",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 2, "similar_negative": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["gender", "noise_scene"],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_dataset_specs_can_be_listed_and_fetched(client):
    spec_id = _create_spec(client)

    list_response = client.get("/api/dataset-specs")
    detail_response = client.get(f"/api/dataset-specs/{spec_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == spec_id
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == spec_id
    assert detail_response.json()["quotas"] == {"wake_positive": 2, "similar_negative": 1}
    assert detail_response.json()["overrides"] == []


def test_preview_reports_shortfalls_without_creating_version(client, wav_factory):
    import_asset(client, wav_factory, "preview_pos.wav", "你好小智", "wake_positive")
    spec_id = _create_spec(client)

    response = client.post(f"/api/dataset-specs/{spec_id}/preview")
    versions = client.get("/api/dataset-versions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_count"] == 1
    assert payload["shortfalls"] == {"wake_positive": 1, "similar_negative": 1}
    assert versions.status_code == 200
    assert versions.json()["items"] == []


def test_preview_and_build_both_include_manual_include_outside_filter(client, wav_factory):
    import_asset(client, wav_factory, "preview_filter_hit.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "preview_manual_include.wav", "你好小智 手动", "wake_positive")
    assets = client.get("/api/assets").json()["items"]
    manual_id = next(item["id"] for item in assets if item["text"] == "你好小智 手动")
    patch = client.patch(f"/api/assets/{manual_id}", json={"gender": "male"})
    assert patch.status_code == 200
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "preview_manual_include",
            "description": "preview should match build for manual includes",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 2},
            "filters": {"quality_status": ["ready"], "gender": ["female"]},
            "balance_by": ["gender"],
        },
    )
    assert spec_response.status_code == 200
    spec_id = spec_response.json()["id"]
    override = client.post(
        f"/api/dataset-specs/{spec_id}/overrides",
        json={"variant_id": manual_id, "action": "include", "reason": "anchor outside filter"},
    )
    assert override.status_code == 200

    preview_response = client.post(f"/api/dataset-specs/{spec_id}/preview")
    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert preview_response.status_code == 200
    assert build_response.status_code == 200
    assert preview_response.json()["candidate_count"] == 2
    assert preview_response.json()["item_count"] == 2
    assert preview_response.json()["counts_by_sample_type"] == {"wake_positive": 2}
    assert build_response.json()["item_count"] == 2


def test_dataset_versions_and_items_can_be_listed_and_fetched(client, wav_factory):
    import_asset(client, wav_factory, "version_pos.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "version_neg.wav", "你好小志", "similar_negative")
    spec_id = _create_spec(client)

    version_response = client.post(f"/api/dataset-specs/{spec_id}/build")
    version_id = version_response.json()["id"]
    list_response = client.get("/api/dataset-versions")
    detail_response = client.get(f"/api/dataset-versions/{version_id}")
    items_response = client.get(f"/api/dataset-versions/{version_id}/items")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == version_id
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == version_id
    assert detail_response.json()["coverage_summary"]["total"] == 2
    assert items_response.status_code == 200
    assert len(items_response.json()["items"]) == 2
    assert items_response.json()["items"][0]["selection_rank"] == 1
