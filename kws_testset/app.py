from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from kws_testset.api.assets import router as assets_router
from kws_testset.api.datasets import router as datasets_router
from kws_testset.api.imports import router as imports_router
from kws_testset.api.taxonomy import router as taxonomy_router
from kws_testset.config import load_config
from kws_testset.db import create_engine_for_config, init_db


def _default_frontend_dist() -> Path:
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _fallback_index() -> str:
    web_path = Path(__file__).parent / "web" / "index.html"
    return web_path.read_text(encoding="utf-8")


def create_app(config_path: str | Path = "configs/app.yaml", frontend_dist: str | Path | None = None) -> FastAPI:
    config = load_config(config_path)
    engine = create_engine_for_config(config)
    init_db(engine)

    app = FastAPI(title="KWS Testset Platform", version="0.1.0")
    app.state.config = config
    app.state.engine = engine

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(imports_router)
    app.include_router(assets_router)
    app.include_router(datasets_router)
    app.include_router(taxonomy_router)

    dist_path = Path(frontend_dist) if frontend_dist is not None else _default_frontend_dist()
    if dist_path.exists() and (dist_path / "index.html").exists():
        app.mount("/ui-static", StaticFiles(directory=dist_path), name="ui-static")

        @app.get("/", response_class=HTMLResponse)
        def index() -> FileResponse:
            return FileResponse(dist_path / "index.html")

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found")
            if full_path.startswith("ui-static/"):
                raise HTTPException(status_code=404, detail="UI asset not found")
            return FileResponse(dist_path / "index.html")
    else:

        @app.get("/", response_class=HTMLResponse)
        def index() -> str:
            return _fallback_index()

    return app
