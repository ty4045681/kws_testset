from pathlib import Path

from fastapi.testclient import TestClient

from kws_testset.app import create_app


def test_api_health_is_not_captured_by_spa_fallback(tmp_path: Path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(f"app:\n  data_dir: {tmp_path / 'data'}\n", encoding="utf-8")
    client = TestClient(create_app(config_path=config_path))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_spa_fallback_serves_index_for_frontend_routes(tmp_path: Path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(f"app:\n  data_dir: {tmp_path / 'data'}\n", encoding="utf-8")
    dist_dir = tmp_path / "frontend_dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html><body><div id='root'>React App</div></body></html>", encoding="utf-8")
    client = TestClient(create_app(config_path=config_path, frontend_dist=dist_dir))

    response = client.get("/assets")

    assert response.status_code == 200
    assert "React App" in response.text
