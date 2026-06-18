import struct


def _write_zero_rate_wav(path):
    fmt_chunk = struct.pack("<HHIIHH", 1, 1, 0, 0, 2, 16)
    data_chunk = b""
    body = b"fmt " + struct.pack("<I", len(fmt_chunk)) + fmt_chunk + b"data" + struct.pack("<I", len(data_chunk)) + data_chunk
    path.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body)


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


def test_failed_batch_import_removes_previously_copied_sources(client, wav_factory):
    valid_path = wav_factory("atomic_valid.wav")
    invalid_path = wav_factory("atomic_invalid.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "partially_bad_batch",
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

    assert response.status_code == 400
    source_root = client.app.state.config.app.data_dir / "library" / "sources"
    assert list(source_root.glob("*.wav")) == []
    assert client.get("/api/assets").json()["items"] == []


def test_draft_import_allows_semantic_mismatch_to_be_fixed_later(client, wav_factory):
    wav_path = wav_factory("draft_mismatch.wav")

    response = client.post(
        "/api/imports",
        json={
            "name": "draft_batch",
            "files": [
                {
                    "path": str(wav_path),
                    "text": "你好小智",
                    "sample_type": "ordinary_negative",
                    "quality_status": "draft",
                }
            ],
        },
    )

    assert response.status_code == 200
    assets = client.get("/api/assets").json()["items"]
    assert assets[0]["quality_status"] == "draft"
    assert assets[0]["sample_type"] == "ordinary_negative"


def test_scan_zero_rate_wav_reports_error_status(client, tmp_path):
    wav_path = tmp_path / "zero_rate.wav"
    _write_zero_rate_wav(wav_path)

    response = client.post("/api/imports/scan", json={"paths": [str(wav_path)]})

    assert response.status_code == 200
    assert response.json()["files"][0]["status"] == "error"
