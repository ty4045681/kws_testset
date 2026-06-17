def test_commit_import_creates_source_and_original_variant(client, wav_factory):
    wav_path = wav_factory("positive.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "batch_one",
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
    assert response.json()["imported_count"] == 1

    assets = client.get("/api/assets").json()["items"]
    assert len(assets) == 1
    assert assets[0]["text"] == "你好小智"
    assert assets[0]["sample_type"] == "wake_positive"
    assert assets[0]["quality_status"] == "ready"


def test_ready_import_rejects_empty_text(client, wav_factory):
    wav_path = wav_factory("empty_text.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "bad_batch",
            "files": [
                {
                    "path": str(wav_path),
                    "text": "",
                    "sample_type": "ordinary_negative",
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

    assert response.status_code == 400
    assert "ready text is required" in response.json()["detail"]


def test_ready_import_rejects_missing_required_metadata(client, wav_factory):
    wav_path = wav_factory("missing_meta.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "bad_batch",
            "files": [
                {
                    "path": str(wav_path),
                    "text": "你好小智",
                    "sample_type": "wake_positive",
                    "quality_status": "ready",
                    "voice_source": "unknown",
                    "gender": "unknown",
                    "age_group": "unknown",
                    "volume": "unknown",
                    "pitch": "normal",
                    "speed": "normal",
                    "noise_scene": "clean",
                    "impairment_type": "none",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "ready volume must not be unknown" in response.json()["detail"]
