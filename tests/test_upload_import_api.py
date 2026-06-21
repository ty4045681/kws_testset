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


def test_upload_wavs_uses_unique_staging_paths_for_sanitized_name_collisions(client, wav_factory):
    first_path = wav_factory("collision_one.wav")
    second_path = wav_factory("collision_two.wav")

    with first_path.open("rb") as first_file, second_path.open("rb") as second_file:
        response = client.post(
            "/api/imports/uploads",
            files=[
                ("files", ("a b.wav", first_file, "audio/wav")),
                ("files", ("a@b.wav", second_file, "audio/wav")),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["uploaded"] == 2
    paths = [row["path"] for row in payload["files"]]
    assert len(set(paths)) == 2
    assert all(Path(path).exists() for path in paths)


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


def test_upload_removes_invalid_wav_from_staging_dir(client, tmp_path: Path):
    broken_wav = tmp_path / "broken.wav"
    broken_wav.write_bytes(b"RIFF not really a wav")

    with broken_wav.open("rb") as wav_file:
        response = client.post(
            "/api/imports/uploads",
            files=[("files", ("broken.wav", wav_file, "audio/wav"))],
        )

    assert response.status_code == 200
    row = response.json()["files"][0]
    assert row["status"] == "error"
    assert not Path(row["path"]).exists()


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
    assert detail_response.json()["failed_count"] == 0


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
    detail_response = client.get(f"/api/imports/{payload['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["failed_count"] == 1
    assets = client.get("/api/assets").json()["items"]
    assert len(assets) == 1
    assert assets[0]["text"] == "你好小智"


def test_partial_commit_reports_copy_failures_per_row_without_rolling_back_successes(client, wav_factory, monkeypatch):
    first_path = wav_factory("partial_copy_good.wav")
    second_path = wav_factory("partial_copy_bad.wav")

    real_copy2 = __import__("shutil").copy2

    def fail_second_copy(src, dst, *args, **kwargs):
        if Path(src).name == "partial_copy_bad.wav":
            raise OSError("synthetic copy failure")
        return real_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr("kws_testset.services.import_service.shutil.copy2", fail_second_copy)

    response = client.post(
        "/api/imports",
        json={
            "name": "partial_copy_failure_case",
            "partial": True,
            "files": [
                {
                    "path": str(first_path),
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
                    "path": str(second_path),
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
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["status"] == "partial"
    assert payload["files"][0]["status"] == "imported"
    assert payload["files"][1]["status"] == "error"
    assert "synthetic copy failure" in payload["files"][1]["errors"][0]
    assets = client.get("/api/assets").json()["items"]
    assert len(assets) == 1
    assert assets[0]["text"] == "你好小智"


def test_partial_commit_marks_all_duplicate_batches_as_duplicate(client, wav_factory):
    wav_path = wav_factory("partial_duplicate.wav")
    base_payload = {
        "name": "duplicate_seed",
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
    }
    seed = client.post("/api/imports", json=base_payload)
    assert seed.status_code == 200

    duplicate_response = client.post("/api/imports", json={**base_payload, "name": "duplicate_partial", "partial": True})

    assert duplicate_response.status_code == 200
    payload = duplicate_response.json()
    assert payload["imported_count"] == 0
    assert payload["duplicate_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["status"] == "duplicate"
    detail_response = client.get(f"/api/imports/{payload['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "duplicate"
    assert detail_response.json()["failed_count"] == 0
