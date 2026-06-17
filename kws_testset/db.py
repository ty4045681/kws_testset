from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from kws_testset.config import AppConfig
import kws_testset.models  # noqa: F401


def create_engine_for_config(config: AppConfig) -> Engine:
    config.app.data_dir.mkdir(parents=True, exist_ok=True)
    db_path = config.app.data_dir / "app.db"
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def create_engine_for_path(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
