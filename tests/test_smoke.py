from pathlib import Path

from sqlmodel import Session, select

from kws_testset.config import AppConfig, load_config
from kws_testset.db import create_engine_for_config, init_db
from kws_testset.models.audio import AudioSource


def test_default_config_loads_and_resolves_data_dir(tmp_path: Path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        "app:\n"
        "  data_dir: data\n"
        "  target_keyword: 你好小智\n"
        "export:\n"
        "  default_audio_mode: reference_original_path\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config, AppConfig)
    assert config.app.target_keyword == "你好小智"
    assert config.app.data_dir == tmp_path / "data"
    assert config.export.default_audio_mode == "reference_original_path"


def test_sqlite_initializes_tables(tmp_path: Path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        "app:\n"
        "  data_dir: data\n"
        "  target_keyword: 你好小智\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    engine = create_engine_for_config(config)

    init_db(engine)

    with Session(engine) as session:
        assert session.exec(select(AudioSource)).all() == []


def test_import_scan_endpoint_returns_wav_metadata(client, wav_factory):
    wav_path = wav_factory("hello.wav")

    response = client.post("/api/imports/scan", json={"paths": [str(wav_path)]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["scanned"] == 1
    assert payload["files"][0]["original_filename"] == "hello.wav"
    assert payload["files"][0]["sample_rate"] == 16000
    assert payload["files"][0]["channels"] == 1
    assert payload["files"][0]["status"] == "can_import"


def test_health_and_taxonomy_endpoints(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    taxonomy = client.get("/api/taxonomy").json()
    assert "wake_positive" in taxonomy["sample_type"]
    assert "device_denoise" in taxonomy["impairment_type"]


def test_web_shell_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "KWS Testset Platform" in response.text
