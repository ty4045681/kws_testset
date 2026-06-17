from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from kws_testset.api.assets import router as assets_router
from kws_testset.api.datasets import router as datasets_router
from kws_testset.api.imports import router as imports_router
from kws_testset.api.taxonomy import router as taxonomy_router
from kws_testset.config import load_config
from kws_testset.db import create_engine_for_config, init_db


def create_app(config_path: str | Path = "configs/app.yaml") -> FastAPI:
    config = load_config(config_path)
    engine = create_engine_for_config(config)
    init_db(engine)

    app = FastAPI(title="KWS Testset Platform", version="0.1.0")
    app.state.config = config
    app.state.engine = engine

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        web_path = Path(__file__).parent / "web" / "index.html"
        return web_path.read_text(encoding="utf-8")

    app.include_router(imports_router)
    app.include_router(assets_router)
    app.include_router(datasets_router)
    app.include_router(taxonomy_router)
    return app
