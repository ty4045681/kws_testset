from pathlib import Path
import wave

import pytest
from fastapi.testclient import TestClient

from kws_testset.app import create_app


@pytest.fixture
def wav_factory(tmp_path: Path):
    def _write(name: str = "sample.wav", seconds: float = 0.1) -> Path:
        path = tmp_path / name
        sample_rate = 16000
        frames = int(sample_rate * seconds)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes([sum(name.encode("utf-8")) % 256, 0]) * frames)
        return path
    return _write


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        f"app:\n  data_dir: {tmp_path / 'data'}\n  target_keyword: 你好小智\n",
        encoding="utf-8",
    )
    return TestClient(create_app(config_path=config_path))
