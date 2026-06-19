from sqlmodel import Session

from kws_testset.models.audio import AudioVariant


def _import_ready_asset(client, wav_factory, name="asset_edit.wav") -> str:
    before = {item["id"] for item in client.get("/api/assets").json()["items"]}
    wav_path = wav_factory(name)
    response = client.post(
        "/api/imports",
        json={
            "name": f"batch_{name}",
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
    after = client.get("/api/assets").json()["items"]
    created = [item for item in after if item["id"] not in before]
    assert len(created) == 1
    return created[0]["id"]


def test_patch_asset_updates_metadata_and_normalized_text(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory)

    response = client.patch(
        f"/api/assets/{asset_id}",
        json={"text": "你好小志", "sample_type": "similar_negative", "quality_status": "ready"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["text"] == "你好小志"
    assert payload["asset"]["normalized_text"] == "你好小志"
    assert payload["asset"]["sample_type"] == "similar_negative"
    assert payload["validation"]["ok"] is True


def test_patch_asset_rejects_invalid_ready_metadata(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory, "invalid_ready.wav")

    response = client.patch(f"/api/assets/{asset_id}", json={"volume": "unknown", "quality_status": "ready"})

    assert response.status_code == 400
    assert "ready volume must not be unknown" in response.json()["detail"]["errors"]


def test_bulk_update_reports_per_asset_results(client, wav_factory):
    first = _import_ready_asset(client, wav_factory, "bulk_one.wav")
    second = _import_ready_asset(client, wav_factory, "bulk_two.wav")

    response = client.post(
        "/api/assets/bulk-update",
        json={"asset_ids": [first, second, "missing"], "patch": {"noise_scene": "office"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated"] == 2
    assert payload["failed"] == 1
    assert payload["results"]["missing"]["ok"] is False
    with Session(client.app.state.engine) as session:
        assert session.get(AudioVariant, first).noise_scene == "office"
        assert session.get(AudioVariant, second).noise_scene == "office"


def test_bulk_update_preserves_success_when_later_existing_asset_fails(client, wav_factory):
    first = _import_ready_asset(client, wav_factory, "bulk_savepoint_good.wav")
    second = _import_ready_asset(client, wav_factory, "bulk_savepoint_bad.wav")
    setup = client.patch(
        f"/api/assets/{first}",
        json={"text": "你好小志", "sample_type": "similar_negative", "quality_status": "ready"},
    )
    assert setup.status_code == 200

    response = client.post(
        "/api/assets/bulk-update",
        json={"asset_ids": [first, second], "patch": {"sample_type": "ordinary_negative"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated"] == 1
    assert payload["failed"] == 1
    assert payload["results"][first]["ok"] is True
    assert payload["results"][second]["ok"] is False
    assert "ordinary_negative text must not contain target keyword" in payload["results"][second]["errors"]
    with Session(client.app.state.engine) as session:
        assert session.get(AudioVariant, first).sample_type == "ordinary_negative"
        assert session.get(AudioVariant, second).sample_type == "wake_positive"


def test_asset_audio_endpoint_streams_wav(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory, "playable.wav")

    response = client.get(f"/api/assets/{asset_id}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")


def test_assets_filter_by_sample_type(client, wav_factory):
    _import_ready_asset(client, wav_factory, "filter_positive.wav")
    asset_id = _import_ready_asset(client, wav_factory, "filter_negative.wav")
    client.patch(f"/api/assets/{asset_id}", json={"text": "你好小志", "sample_type": "similar_negative"})

    response = client.get("/api/assets?sample_type=similar_negative")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["sample_type"] == "similar_negative"


def test_assets_filter_before_pagination(client, wav_factory):
    _import_ready_asset(client, wav_factory, "page_positive_one.wav")
    _import_ready_asset(client, wav_factory, "page_positive_two.wav")
    asset_id = _import_ready_asset(client, wav_factory, "page_negative.wav")
    patch = client.patch(f"/api/assets/{asset_id}", json={"text": "你好小志", "sample_type": "similar_negative"})
    assert patch.status_code == 200

    response = client.get("/api/assets?sample_type=similar_negative&limit=1&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == asset_id
