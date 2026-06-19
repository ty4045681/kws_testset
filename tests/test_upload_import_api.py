from pathlib import Path


def test_upload_wavs_returns_probe_rows_and_staging_paths(client, wav_factory):
    wav_path = wav_factory("browser_upload.wav")

    with wav_path.open("rb") as wav_file:
        response = client.post(
            "/api/imports/uploads",
            files=[("files", ("browser_upload.wav", wav_file, "audio/wav"))],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["uploaded"] == 1
    assert payload["failed"] == 0
    assert len(payload["files"]) == 1
    row = payload["files"][0]
    assert row["original_filename"] == "browser_upload.wav"
    assert row["status"] == "can_import"
    assert row["path"].endswith("browser_upload.wav")
    assert Path(row["path"]).exists()
    assert row["sample_rate"] == 16000
    assert row["channels"] == 1


def test_upload_rejects_non_wav_as_failed_row(client, tmp_path: Path):
    text_path = tmp_path / "not_audio.txt"
    text_path.write_text("not a wav", encoding="utf-8")

    with text_path.open("rb") as text_file:
        response = client.post(
            "/api/imports/uploads",
            files=[("files", ("not_audio.txt", text_file, "text/plain"))],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["uploaded"] == 0
    assert payload["failed"] == 1
    assert payload["files"][0]["status"] == "error"
    assert "WAV" in payload["files"][0]["error"]


def test_import_batches_can_be_listed_and_fetched(client, wav_factory):
    wav_path = wav_factory("batch_list.wav")
    response = client.post(
        "/api/imports",
        json={
            "name": "batch_list_case",
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
    batch_id = response.json()["id"]

    list_response = client.get("/api/imports")
    detail_response = client.get(f"/api/imports/{batch_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["name"] == "batch_list_case"
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == batch_id
    assert detail_response.json()["imported_count"] == 1


def test_partial_commit_imports_valid_rows_and_reports_invalid_rows(client, wav_factory):
    valid_path = wav_factory("partial_valid.wav")
    invalid_path = wav_factory("partial_invalid.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "partial_commit_case",
            "partial": True,
            "files": [
                {
                    "path": str(valid_path),
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
                },
                {
                    "path": str(invalid_path),
                    "text": "",
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
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["files"][0]["status"] == "imported"
    assert payload["files"][1]["status"] == "error"
    assert "ready text is required" in payload["files"][1]["errors"]
    assets = client.get("/api/assets").json()["items"]
    assert len(assets) == 1
    assert assets[0]["text"] == "你好小智"
