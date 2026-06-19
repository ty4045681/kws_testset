# KWS Testset Platform UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first complete React/Vite platform UI for the KWS testset system, including browser WAV upload, metadata editing, asset management, dataset building, version export, and FastAPI static serving.

**Architecture:** Keep FastAPI as the single backend and source of truth for validation, sampling, export, audio streaming, and persistence. Add only the backend APIs required to close the UI workflow, then build a React + Vite + TypeScript frontend under `frontend/` that can run in dev mode through a Vite proxy and in integrated mode through FastAPI static serving. Preserve cross-platform commands and avoid bash-only runtime entrypoints.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, pytest, httpx/TestClient, React 18, Vite, TypeScript, npm, native browser audio playback.

---

## Scope Check

This plan implements one cohesive subsystem: the first full platform UI and the backend API additions needed by that UI. It does not implement generation/enhancement jobs, evaluation result ingestion, model execution, multi-user workflows, dynamic taxonomy editing, or full E2E testing.

The plan produces working software after every task:

1. Backend static serving and dependency setup.
2. Upload/import listing APIs and explicit partial commit mode.
3. Asset edit/audio APIs.
4. Dataset preview/list/detail APIs.
5. Frontend scaffold, layout, API client, and types.
6. Import + Assets pages.
7. Dataset Builder + Versions/Export pages.
8. Dashboard + Settings + README.
9. Final cross-platform verification.

## File Structure

Create or modify these files.

Backend:

```text
/Users/e4/Documents/kws_testset/pyproject.toml
/Users/e4/Documents/kws_testset/README.md
/Users/e4/Documents/kws_testset/kws_testset/app.py
/Users/e4/Documents/kws_testset/kws_testset/api/imports.py
/Users/e4/Documents/kws_testset/kws_testset/api/assets.py
/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py
/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py
/Users/e4/Documents/kws_testset/kws_testset/services/import_upload_service.py
/Users/e4/Documents/kws_testset/kws_testset/services/asset_service.py
/Users/e4/Documents/kws_testset/kws_testset/services/dataset_selection_service.py
/Users/e4/Documents/kws_testset/kws_testset/services/dataset_preview_service.py
```

Backend tests:

```text
/Users/e4/Documents/kws_testset/tests/test_static_serving.py
/Users/e4/Documents/kws_testset/tests/test_upload_import_api.py
/Users/e4/Documents/kws_testset/tests/test_asset_edit_api.py
/Users/e4/Documents/kws_testset/tests/test_dataset_browse_api.py
```

Frontend:

```text
/Users/e4/Documents/kws_testset/frontend/package.json
/Users/e4/Documents/kws_testset/frontend/index.html
/Users/e4/Documents/kws_testset/frontend/tsconfig.json
/Users/e4/Documents/kws_testset/frontend/vite.config.ts
/Users/e4/Documents/kws_testset/frontend/src/main.tsx
/Users/e4/Documents/kws_testset/frontend/src/App.tsx
/Users/e4/Documents/kws_testset/frontend/src/styles.css
/Users/e4/Documents/kws_testset/frontend/src/api/client.ts
/Users/e4/Documents/kws_testset/frontend/src/types/api.ts
/Users/e4/Documents/kws_testset/frontend/src/components/AudioPlayer.tsx
/Users/e4/Documents/kws_testset/frontend/src/components/BulkEditToolbar.tsx
/Users/e4/Documents/kws_testset/frontend/src/components/CoveragePanel.tsx
/Users/e4/Documents/kws_testset/frontend/src/components/ErrorSummary.tsx
/Users/e4/Documents/kws_testset/frontend/src/components/StatusBadge.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/DashboardPage.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/ImportPage.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/AssetsPage.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/DatasetBuilderPage.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/VersionsPage.tsx
/Users/e4/Documents/kws_testset/frontend/src/pages/SettingsPage.tsx
```

Frontend responsibilities:

- `api/client.ts`: one typed fetch wrapper and all endpoint functions.
- `types/api.ts`: hand-written types matching backend responses.
- `App.tsx`: local tab navigation; no router dependency in first version.
- `components/*`: small reusable visual/interaction components.
- `pages/*`: workflow orchestration only; backend remains validation authority.

---

### Task 1: FastAPI Static Serving and Frontend Dependency Setup

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/pyproject.toml`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_static_serving.py`
- Create: `/Users/e4/Documents/kws_testset/frontend/package.json`
- Create: `/Users/e4/Documents/kws_testset/frontend/index.html`
- Create: `/Users/e4/Documents/kws_testset/frontend/tsconfig.json`
- Create: `/Users/e4/Documents/kws_testset/frontend/vite.config.ts`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/main.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/App.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/styles.css`

- [ ] **Step 1: Write the failing static serving test**

Create `/Users/e4/Documents/kws_testset/tests/test_static_serving.py`:

```python
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
```

- [ ] **Step 2: Run the static serving test to verify it fails**

Run:

```bash
uv run python -m pytest tests/test_static_serving.py -v
```

Expected: FAIL with `TypeError: create_app() got an unexpected keyword argument 'frontend_dist'`.

- [ ] **Step 3: Add backend dependencies**

Modify `/Users/e4/Documents/kws_testset/pyproject.toml` so the dependencies list contains `python-multipart` for upcoming browser uploads:

```toml
[project]
name = "kws-testset"
version = "0.1.0"
description = "Local KWS testset creation and management platform"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "sqlmodel>=0.0.22",
  "typer>=0.12.0",
  "uvicorn[standard]>=0.30.0",
  "pyyaml>=6.0.0",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "httpx>=0.27.0",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools.packages.find]
include = ["kws_testset*"]
```

- [ ] **Step 4: Implement FastAPI static serving and SPA fallback**

Replace `/Users/e4/Documents/kws_testset/kws_testset/app.py` with:

```python
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
```

- [ ] **Step 5: Add minimal frontend scaffold**

Create `/Users/e4/Documents/kws_testset/frontend/package.json`:

```json
{
  "name": "kws-testset-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc --noEmit && vite build",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "@vitejs/plugin-react": "4.3.4",
    "typescript": "5.6.3",
    "vite": "5.4.11"
  }
}
```

Create `/Users/e4/Documents/kws_testset/frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KWS Testset Platform</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `/Users/e4/Documents/kws_testset/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
```

Create `/Users/e4/Documents/kws_testset/frontend/vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/ui-static/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
});
```

Create `/Users/e4/Documents/kws_testset/frontend/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `/Users/e4/Documents/kws_testset/frontend/src/App.tsx`:

```tsx
export function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">Wake Testset</div>
        <button className="nav-item active">Dashboard</button>
        <button className="nav-item">Import Wizard</button>
        <button className="nav-item">Assets</button>
        <button className="nav-item">Dataset Builder</button>
        <button className="nav-item">Versions / Export</button>
        <button className="nav-item">Settings</button>
      </aside>
      <section className="content">
        <h1>KWS Testset Platform</h1>
        <p>React UI scaffold is ready.</p>
      </section>
    </main>
  );
}
```

Create `/Users/e4/Documents/kws_testset/frontend/src/styles.css`:

```css
:root {
  color: #e5e7eb;
  background: #0f172a;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

button, input, select, textarea {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  background: #0f172a;
}

.sidebar {
  width: 240px;
  padding: 20px;
  background: #111827;
  border-right: 1px solid #1f2937;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.brand {
  font-weight: 700;
  font-size: 18px;
  margin-bottom: 16px;
}

.nav-item {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  color: #cbd5e1;
  background: #1f2937;
  text-align: left;
  cursor: pointer;
}

.nav-item.active,
.nav-item:hover {
  color: #ffffff;
  background: #2563eb;
}

.content {
  flex: 1;
  padding: 28px;
}
```

- [ ] **Step 6: Run backend test and frontend build**

Run:

```bash
uv sync --extra dev
uv run python -m pytest tests/test_static_serving.py -v
cd frontend && npm install && npm run typecheck && npm run build
```

Expected:

- `tests/test_static_serving.py` passes.
- `npm run typecheck` exits 0.
- `npm run build` exits 0 and creates `/Users/e4/Documents/kws_testset/frontend/dist/index.html`.

- [ ] **Step 7: Commit Task 1**

```bash
git add pyproject.toml uv.lock kws_testset/app.py tests/test_static_serving.py frontend/package.json frontend/index.html frontend/tsconfig.json frontend/vite.config.ts frontend/src/main.tsx frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat: scaffold React UI and static serving"
```

---

### Task 2: Browser WAV Upload, Partial Commit, and Import Batch Browse APIs

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/import_upload_service.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_upload_import_api.py`

- [ ] **Step 1: Write failing upload and import browse tests**

Create `/Users/e4/Documents/kws_testset/tests/test_upload_import_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run python -m pytest tests/test_upload_import_api.py -v
```

Expected: FAIL with 404 for `/api/imports/uploads` or `/api/imports` GET.
The partial commit test may instead fail with 400 until `partial=true` support is added.

- [ ] **Step 3: Implement upload service**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/import_upload_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import wave

from fastapi import UploadFile
from sqlmodel import Session, select

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioSource
from kws_testset.services.audio_probe import probe_wav
from kws_testset.utils.ids import new_id


@dataclass(frozen=True)
class UploadedAudioRow:
    path: Path
    original_filename: str
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str
    status: str
    error: str | None = None


def safe_upload_filename(filename: str) -> str:
    name = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not cleaned:
        cleaned = "upload.wav"
    return cleaned


def save_uploads(files: list[UploadFile], config: AppConfig, session: Session) -> tuple[str, list[UploadedAudioRow]]:
    upload_id = new_id("upl")
    upload_dir = config.app.data_dir / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    rows: list[UploadedAudioRow] = []

    for index, upload in enumerate(files):
        original_filename = upload.filename or f"upload_{index}.wav"
        filename = safe_upload_filename(original_filename)
        destination = upload_dir / filename

        if not filename.lower().endswith(".wav"):
            rows.append(UploadedAudioRow(destination, original_filename, 0.0, 0, 0, 0, "error", "Only WAV files are supported"))
            continue

        with destination.open("wb") as output:
            shutil.copyfileobj(upload.file, output)

        try:
            probe = probe_wav(destination)
        except (OSError, EOFError, ValueError, wave.Error) as exc:
            rows.append(UploadedAudioRow(destination, filename, 0.0, 0, 0, 0, "error", f"Invalid WAV file: {exc}"))
            continue

        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        status = "duplicate" if existing else "can_import"
        rows.append(
            UploadedAudioRow(
                path=probe.path,
                original_filename=filename,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                bit_depth=probe.bit_depth,
                sha256=probe.sha256,
                status=status,
            )
        )

    return upload_id, rows
```

- [ ] **Step 4: Add partial import commit service**

Modify `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py` by keeping the existing atomic `commit_import_batch()` and adding these dataclasses plus `commit_import_batch_partial()` below it:

```python
@dataclass(frozen=True)
class ImportFileCommitResult:
    path: str
    status: str
    errors: list[str]


@dataclass(frozen=True)
class PartialImportResult:
    batch: ImportBatch
    files: list[ImportFileCommitResult]


def commit_import_batch_partial(name: str, files: list[dict[str, Any]], config: AppConfig, session: Session) -> PartialImportResult:
    batch_id = new_id("imp")
    batch = ImportBatch(id=batch_id, name=name, file_count=len(files), status="imported")
    session.add(batch)

    source_root = config.app.data_dir / "library" / "sources"
    source_root.mkdir(parents=True, exist_ok=True)

    imported_count = 0
    duplicate_count = 0
    failed_count = 0
    copied_paths: list[Path] = []
    results: list[ImportFileCommitResult] = []
    try:
        for item in files:
            path_text = str(item["path"])
            try:
                probe = probe_wav(item["path"])
            except (OSError, EOFError, ValueError, wave.Error):
                failed_count += 1
                results.append(ImportFileCommitResult(path_text, "error", [f"invalid WAV file: {path_text}"]))
                continue
            existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
            if existing:
                duplicate_count += 1
                results.append(ImportFileCommitResult(path_text, "duplicate", []))
                continue

            ready_check = validate_ready_metadata(item, probe.duration_sec, config.app.target_keyword)
            if not ready_check.ok:
                failed_count += 1
                results.append(ImportFileCommitResult(path_text, "error", ready_check.errors))
                continue

            source_id = dated_id("src", probe.sha256)
            variant_id = dated_id("var", probe.sha256)
            stored_path = source_root / f"{source_id}.wav"
            shutil.copy2(probe.path, stored_path)
            copied_paths.append(stored_path)

            source = AudioSource(
                id=source_id,
                original_filename=probe.path.name,
                stored_path=str(stored_path.resolve()),
                sha256=probe.sha256,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                bit_depth=probe.bit_depth,
                import_batch_id=batch_id,
            )
            variant = AudioVariant(
                id=variant_id,
                source_id=source_id,
                variant_kind="original",
                stored_path=str(stored_path.resolve()),
                sha256=probe.sha256,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                text=item["text"],
                normalized_text=normalize_text(item["text"]),
                sample_type=item["sample_type"],
                quality_status=item.get("quality_status", "draft"),
                voice_source=item.get("voice_source", "unknown"),
                gender=item.get("gender", "unknown"),
                age_group=item.get("age_group", "unknown"),
                volume=item.get("volume", "unknown"),
                pitch=item.get("pitch", "unknown"),
                speed=item.get("speed", "unknown"),
                noise_scene=item.get("noise_scene", "unknown"),
                impairment_type=item.get("impairment_type", "none"),
                notes=item.get("notes"),
            )
            session.add(source)
            session.add(variant)
            imported_count += 1
            results.append(ImportFileCommitResult(path_text, "imported", []))

        batch.imported_count = imported_count
        batch.duplicate_count = duplicate_count
        batch.status = "imported" if failed_count == 0 else "partial"
        batch.completed_at = datetime.now(timezone.utc)
        session.add(batch)
        session.commit()
    except Exception:
        session.rollback()
        for path in copied_paths:
            path.unlink(missing_ok=True)
        raise
    session.refresh(batch)
    return PartialImportResult(batch=batch, files=results)
```

- [ ] **Step 5: Add upload, partial commit, and import browse routes**

Modify `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py`:

- Add imports:

```python
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlmodel import Session, select

from kws_testset.models.import_batch import ImportBatch
from kws_testset.services.import_service import commit_import_batch, commit_import_batch_partial, scan_wav_paths
from kws_testset.services.import_upload_service import save_uploads
```

- Add `partial` to `CommitImportRequest`:

```python
class CommitImportRequest(BaseModel):
    name: str
    files: list[ImportFileRequest]
    partial: bool = False
```

- Replace the existing `commit_import` route with:

```python
@router.post("")
def commit_import(payload: CommitImportRequest, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    if payload.partial:
        with Session(engine) as session:
            result = commit_import_batch_partial(
                name=payload.name,
                files=[item.model_dump() for item in payload.files],
                config=config,
                session=session,
            )
        batch = result.batch
        return {
            "id": batch.id,
            "name": batch.name,
            "imported_count": batch.imported_count,
            "duplicate_count": batch.duplicate_count,
            "failed_count": sum(1 for item in result.files if item.status == "error"),
            "status": batch.status,
            "files": [
                {"path": item.path, "status": item.status, "errors": item.errors}
                for item in result.files
            ],
        }

    try:
        with Session(engine) as session:
            batch = commit_import_batch(
                name=payload.name,
                files=[item.model_dump() for item in payload.files],
                config=config,
                session=session,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": batch.id,
        "name": batch.name,
        "imported_count": batch.imported_count,
        "duplicate_count": batch.duplicate_count,
        "failed_count": 0,
        "status": batch.status,
        "files": [],
    }
```

- Keep existing `scan_imports` route.
- Add helper and routes before or after existing routes:

```python
def _batch_payload(batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "name": batch.name,
        "source_directory": batch.source_directory,
        "file_count": batch.file_count,
        "imported_count": batch.imported_count,
        "duplicate_count": batch.duplicate_count,
        "status": batch.status,
        "created_at": batch.created_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


@router.post("/uploads")
def upload_import_files(request: Request, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    with Session(engine) as session:
        upload_id, rows = save_uploads(files, config, session)
    return {
        "upload_id": upload_id,
        "uploaded": sum(1 for row in rows if row.status in {"can_import", "duplicate"}),
        "failed": sum(1 for row in rows if row.status == "error"),
        "files": [
            {
                "path": str(row.path),
                "original_filename": row.original_filename,
                "duration_sec": row.duration_sec,
                "sample_rate": row.sample_rate,
                "channels": row.channels,
                "bit_depth": row.bit_depth,
                "sha256": row.sha256,
                "status": row.status,
                "error": row.error,
            }
            for row in rows
        ],
    }


@router.get("")
def list_import_batches(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        batches = session.exec(select(ImportBatch).order_by(ImportBatch.created_at.desc())).all()
    return {"items": [_batch_payload(batch) for batch in batches]}


@router.get("/{batch_id}")
def get_import_batch(batch_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import batch not found")
    return _batch_payload(batch)
```

- [ ] **Step 6: Run upload/import tests and existing import tests**

Run:

```bash
uv run python -m pytest tests/test_upload_import_api.py tests/test_import_and_assets.py -v
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add kws_testset/services/import_upload_service.py kws_testset/services/import_service.py kws_testset/api/imports.py tests/test_upload_import_api.py
git commit -m "feat: add browser upload import APIs"
```

---

### Task 3: Asset Filtering, Editing, Bulk Editing, and Audio Playback API

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/asset_service.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/api/assets.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_asset_edit_api.py`

- [ ] **Step 1: Write failing asset API tests**

Create `/Users/e4/Documents/kws_testset/tests/test_asset_edit_api.py`:

```python
from sqlmodel import Session

from kws_testset.models.audio import AudioVariant


def _import_ready_asset(client, wav_factory, name="asset_edit.wav") -> str:
    before = {item["id"] for item in client.get("/api/assets").json()["items"]}
    wav_path = wav_factory(name)
    response = client.post(
        "/api/imports",
        json={
            "name": f"batch_{name}",
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
    after = client.get("/api/assets").json()["items"]
    created = [item for item in after if item["id"] not in before]
    assert len(created) == 1
    return created[0]["id"]


def test_patch_asset_updates_metadata_and_normalized_text(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory)

    response = client.patch(
        f"/api/assets/{asset_id}",
        json={"text": "你好小志", "sample_type": "similar_negative", "quality_status": "ready"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["text"] == "你好小志"
    assert payload["asset"]["normalized_text"] == "你好小志"
    assert payload["asset"]["sample_type"] == "similar_negative"
    assert payload["validation"]["ok"] is True


def test_patch_asset_rejects_invalid_ready_metadata(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory, "invalid_ready.wav")

    response = client.patch(f"/api/assets/{asset_id}", json={"volume": "unknown", "quality_status": "ready"})

    assert response.status_code == 400
    assert "ready volume must not be unknown" in response.json()["detail"]["errors"]


def test_bulk_update_reports_per_asset_results(client, wav_factory):
    first = _import_ready_asset(client, wav_factory, "bulk_one.wav")
    second = _import_ready_asset(client, wav_factory, "bulk_two.wav")

    response = client.post(
        "/api/assets/bulk-update",
        json={"asset_ids": [first, second, "missing"], "patch": {"noise_scene": "office"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated"] == 2
    assert payload["failed"] == 1
    assert payload["results"]["missing"]["ok"] is False
    with Session(client.app.state.engine) as session:
        assert session.get(AudioVariant, first).noise_scene == "office"
        assert session.get(AudioVariant, second).noise_scene == "office"


def test_bulk_update_preserves_success_when_later_existing_asset_fails(client, wav_factory):
    first = _import_ready_asset(client, wav_factory, "bulk_savepoint_good.wav")
    second = _import_ready_asset(client, wav_factory, "bulk_savepoint_bad.wav")
    setup = client.patch(
        f"/api/assets/{first}",
        json={"text": "你好小志", "sample_type": "similar_negative", "quality_status": "ready"},
    )
    assert setup.status_code == 200

    response = client.post(
        "/api/assets/bulk-update",
        json={"asset_ids": [first, second], "patch": {"sample_type": "ordinary_negative"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated"] == 1
    assert payload["failed"] == 1
    assert payload["results"][first]["ok"] is True
    assert payload["results"][second]["ok"] is False
    assert "ordinary_negative text must not contain target keyword" in payload["results"][second]["errors"]
    with Session(client.app.state.engine) as session:
        assert session.get(AudioVariant, first).sample_type == "ordinary_negative"
        assert session.get(AudioVariant, second).sample_type == "wake_positive"


def test_asset_audio_endpoint_streams_wav(client, wav_factory):
    asset_id = _import_ready_asset(client, wav_factory, "playable.wav")

    response = client.get(f"/api/assets/{asset_id}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")


def test_assets_filter_by_sample_type(client, wav_factory):
    _import_ready_asset(client, wav_factory, "filter_positive.wav")
    asset_id = _import_ready_asset(client, wav_factory, "filter_negative.wav")
    client.patch(f"/api/assets/{asset_id}", json={"text": "你好小志", "sample_type": "similar_negative"})

    response = client.get("/api/assets?sample_type=similar_negative")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["sample_type"] == "similar_negative"


def test_assets_filter_before_pagination(client, wav_factory):
    _import_ready_asset(client, wav_factory, "page_positive_one.wav")
    _import_ready_asset(client, wav_factory, "page_positive_two.wav")
    asset_id = _import_ready_asset(client, wav_factory, "page_negative.wav")
    patch = client.patch(f"/api/assets/{asset_id}", json={"text": "你好小志", "sample_type": "similar_negative"})
    assert patch.status_code == 200

    response = client.get("/api/assets?sample_type=similar_negative&limit=1&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == asset_id
```

- [ ] **Step 2: Run asset API tests to verify they fail**

Run:

```bash
uv run python -m pytest tests/test_asset_edit_api.py -v
```

Expected: FAIL with 404/405 for PATCH, bulk update, or audio endpoint.

- [ ] **Step 3: Implement asset service**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/asset_service.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioVariant
from kws_testset.services.text_normalize import normalize_text
from kws_testset.services.validation_service import ValidationResult, validate_ready_metadata
from kws_testset.taxonomy import as_dict

EDITABLE_FIELDS = {
    "text",
    "sample_type",
    "quality_status",
    "voice_source",
    "speaker_id",
    "gender",
    "age_group",
    "volume",
    "pitch",
    "speed",
    "noise_scene",
    "snr_bucket",
    "impairment_type",
    "notes",
}


def asset_payload(item: AudioVariant, config: AppConfig) -> dict[str, Any]:
    validation = asset_validation_payload(item, config)
    return {
        "id": item.id,
        "source_id": item.source_id,
        "stored_path": item.stored_path,
        "text": item.text,
        "normalized_text": item.normalized_text,
        "sample_type": item.sample_type,
        "quality_status": item.quality_status,
        "voice_source": item.voice_source,
        "speaker_id": item.speaker_id,
        "gender": item.gender,
        "age_group": item.age_group,
        "volume": item.volume,
        "pitch": item.pitch,
        "speed": item.speed,
        "noise_scene": item.noise_scene,
        "snr_bucket": item.snr_bucket,
        "impairment_type": item.impairment_type,
        "variant_kind": item.variant_kind,
        "duration_sec": item.duration_sec,
        "sample_rate": item.sample_rate,
        "channels": item.channels,
        "notes": item.notes,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "validation": validation,
    }


def asset_validation_payload(item: AudioVariant, config: AppConfig) -> dict[str, Any]:
    result = validate_ready_metadata(asset_metadata_dict(item), item.duration_sec, config.app.target_keyword)
    return {"ok": result.ok, "errors": result.errors, "warnings": result.warnings}


def asset_metadata_dict(item: AudioVariant) -> dict[str, Any]:
    return {
        "text": item.text,
        "sample_type": item.sample_type,
        "quality_status": item.quality_status,
        "voice_source": item.voice_source,
        "gender": item.gender,
        "age_group": item.age_group,
        "volume": item.volume,
        "pitch": item.pitch,
        "speed": item.speed,
        "noise_scene": item.noise_scene,
        "impairment_type": item.impairment_type,
    }


def apply_asset_patch(item: AudioVariant, patch: dict[str, Any], config: AppConfig) -> ValidationResult:
    taxonomy = as_dict()
    for key, value in patch.items():
        if key not in EDITABLE_FIELDS:
            return ValidationResult(False, [f"field is not editable: {key}"], [])
        if key in taxonomy and value not in taxonomy[key]:
            return ValidationResult(False, [f"{key} has invalid value: {value}"], [])
        setattr(item, key, value)

    item.normalized_text = normalize_text(item.text)
    validation = validate_ready_metadata(asset_metadata_dict(item), item.duration_sec, config.app.target_keyword)
    if not validation.ok:
        return validation
    item.updated_at = datetime.now(timezone.utc)
    return validation
```

- [ ] **Step 4: Replace asset API**

Replace `/Users/e4/Documents/kws_testset/kws_testset/api/assets.py` with:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.services.asset_service import apply_asset_patch, asset_payload

router = APIRouter(prefix="/api/assets", tags=["assets"])

FILTERABLE_FIELDS = {
    "sample_type",
    "quality_status",
    "voice_source",
    "gender",
    "age_group",
    "volume",
    "pitch",
    "speed",
    "noise_scene",
    "impairment_type",
    "variant_kind",
}


class AssetPatchRequest(BaseModel):
    text: str | None = None
    sample_type: str | None = None
    quality_status: str | None = None
    voice_source: str | None = None
    speaker_id: str | None = None
    gender: str | None = None
    age_group: str | None = None
    volume: str | None = None
    pitch: str | None = None
    speed: str | None = None
    noise_scene: str | None = None
    snr_bucket: str | None = None
    impairment_type: str | None = None
    notes: str | None = None


class BulkUpdateRequest(BaseModel):
    asset_ids: list[str]
    patch: dict[str, Any]


def _extract_patch(payload: AssetPatchRequest) -> dict[str, Any]:
    return {key: value for key, value in payload.model_dump().items() if value is not None}


@router.get("")
def list_assets(request: Request, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    engine = request.app.state.engine
    config = request.app.state.config
    query = select(AudioVariant)
    count_query = select(func.count()).select_from(AudioVariant)
    query_params = dict(request.query_params)
    for field, value in query_params.items():
        if field in FILTERABLE_FIELDS:
            condition = getattr(AudioVariant, field) == value
            query = query.where(condition)
            count_query = count_query.where(condition)
    query = query.order_by(AudioVariant.created_at).offset(offset).limit(limit)
    with Session(engine) as session:
        variants = session.exec(query).all()
        total = session.exec(count_query).one()
    return {"items": [asset_payload(item, config) for item in variants], "limit": limit, "offset": offset, "count": len(variants), "total": total}


@router.patch("/{asset_id}")
def patch_asset(asset_id: str, payload: AssetPatchRequest, request: Request) -> dict[str, Any]:
    config = request.app.state.config
    with Session(request.app.state.engine) as session:
        item = session.get(AudioVariant, asset_id)
        if item is None:
            raise HTTPException(status_code=404, detail="asset not found")
        validation = apply_asset_patch(item, _extract_patch(payload), config)
        if not validation.ok:
            session.rollback()
            raise HTTPException(status_code=400, detail={"errors": validation.errors, "warnings": validation.warnings})
        session.add(item)
        session.commit()
        session.refresh(item)
        return {"asset": asset_payload(item, config), "validation": {"ok": validation.ok, "errors": validation.errors, "warnings": validation.warnings}}


@router.post("/bulk-update")
def bulk_update_assets(payload: BulkUpdateRequest, request: Request) -> dict[str, Any]:
    config = request.app.state.config
    results: dict[str, Any] = {}
    updated = 0
    failed = 0
    with Session(request.app.state.engine) as session:
        for asset_id in payload.asset_ids:
            savepoint = session.begin_nested()
            try:
                item = session.get(AudioVariant, asset_id)
                if item is None:
                    savepoint.rollback()
                    failed += 1
                    results[asset_id] = {"ok": False, "errors": ["asset not found"], "warnings": []}
                    continue
                validation = apply_asset_patch(item, payload.patch, config)
                if not validation.ok:
                    savepoint.rollback()
                    failed += 1
                    results[asset_id] = {"ok": False, "errors": validation.errors, "warnings": validation.warnings}
                    continue
                session.add(item)
                savepoint.commit()
                updated += 1
                results[asset_id] = {"ok": True, "errors": [], "warnings": validation.warnings}
            except Exception:
                savepoint.rollback()
                raise
        session.commit()
    return {"updated": updated, "failed": failed, "results": results}


@router.get("/{asset_id}/audio")
def stream_asset_audio(asset_id: str, request: Request) -> FileResponse:
    with Session(request.app.state.engine) as session:
        item = session.get(AudioVariant, asset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="asset not found")
    path = Path(item.stored_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="audio file not found")
    return FileResponse(path, media_type="audio/wav", filename=path.name)
```

- [ ] **Step 5: Run asset tests and full backend tests**

Run:

```bash
uv run python -m pytest tests/test_asset_edit_api.py tests/test_import_and_assets.py -v
uv run python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add kws_testset/services/asset_service.py kws_testset/api/assets.py tests/test_asset_edit_api.py
git commit -m "feat: add asset edit and playback APIs"
```

---

### Task 4: Dataset Spec Browse, Preview, Version Browse, and Items APIs

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/dataset_selection_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/dataset_preview_service.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_dataset_browse_api.py`

- [ ] **Step 1: Write failing dataset browse tests**

Create `/Users/e4/Documents/kws_testset/tests/test_dataset_browse_api.py`:

```python
from tests.test_dataset_build_api import import_asset


def _create_spec(client):
    response = client.post(
        "/api/dataset-specs",
        json={
            "name": "browse_spec",
            "description": "browse api spec",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 2, "similar_negative": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["gender", "noise_scene"],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_dataset_specs_can_be_listed_and_fetched(client):
    spec_id = _create_spec(client)

    list_response = client.get("/api/dataset-specs")
    detail_response = client.get(f"/api/dataset-specs/{spec_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == spec_id
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == spec_id
    assert detail_response.json()["quotas"] == {"wake_positive": 2, "similar_negative": 1}
    assert detail_response.json()["overrides"] == []


def test_preview_reports_shortfalls_without_creating_version(client, wav_factory):
    import_asset(client, wav_factory, "preview_pos.wav", "你好小智", "wake_positive")
    spec_id = _create_spec(client)

    response = client.post(f"/api/dataset-specs/{spec_id}/preview")
    versions = client.get("/api/dataset-versions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_count"] == 1
    assert payload["shortfalls"] == {"wake_positive": 1, "similar_negative": 1}
    assert versions.status_code == 200
    assert versions.json()["items"] == []


def test_preview_and_build_both_include_manual_include_outside_filter(client, wav_factory):
    import_asset(client, wav_factory, "preview_filter_hit.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "preview_manual_include.wav", "你好小智 手动", "wake_positive")
    assets = client.get("/api/assets").json()["items"]
    manual_id = next(item["id"] for item in assets if item["text"] == "你好小智 手动")
    patch = client.patch(f"/api/assets/{manual_id}", json={"gender": "male"})
    assert patch.status_code == 200
    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "preview_manual_include",
            "description": "preview should match build for manual includes",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 2},
            "filters": {"quality_status": ["ready"], "gender": ["female"]},
            "balance_by": ["gender"],
        },
    )
    assert spec_response.status_code == 200
    spec_id = spec_response.json()["id"]
    override = client.post(
        f"/api/dataset-specs/{spec_id}/overrides",
        json={"variant_id": manual_id, "action": "include", "reason": "anchor outside filter"},
    )
    assert override.status_code == 200

    preview_response = client.post(f"/api/dataset-specs/{spec_id}/preview")
    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert preview_response.status_code == 200
    assert build_response.status_code == 200
    assert preview_response.json()["candidate_count"] == 2
    assert preview_response.json()["item_count"] == 2
    assert preview_response.json()["counts_by_sample_type"] == {"wake_positive": 2}
    assert build_response.json()["item_count"] == 2


def test_dataset_versions_and_items_can_be_listed_and_fetched(client, wav_factory):
    import_asset(client, wav_factory, "version_pos.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "version_neg.wav", "你好小志", "similar_negative")
    spec_id = _create_spec(client)

    version_response = client.post(f"/api/dataset-specs/{spec_id}/build")
    version_id = version_response.json()["id"]
    list_response = client.get("/api/dataset-versions")
    detail_response = client.get(f"/api/dataset-versions/{version_id}")
    items_response = client.get(f"/api/dataset-versions/{version_id}/items")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == version_id
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == version_id
    assert detail_response.json()["coverage_summary"]["total"] == 2
    assert items_response.status_code == 200
    assert len(items_response.json()["items"]) == 2
    assert items_response.json()["items"][0]["selection_rank"] == 1
```

- [ ] **Step 2: Run dataset browse tests to verify they fail**

Run:

```bash
uv run python -m pytest tests/test_dataset_browse_api.py -v
```

Expected: FAIL with 405/404 for GET spec, preview, versions, or items endpoints.

- [ ] **Step 3: Extract shared dataset selection service, then add preview service**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/dataset_selection_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.models.dataset import DatasetSpec, ManualOverride
from kws_testset.services.coverage_service import build_coverage_summary
from kws_testset.services.sampling_service import ManualOverrideInput, SampleCandidate, SamplingResult, SelectedSample, sample_candidates


@dataclass(frozen=True)
class SpecSelection:
    variants: list[AudioVariant]
    selected_variants: list[AudioVariant]
    selected_by_id: dict[str, SelectedSample]
    overrides: list[ManualOverride]
    snapshots: list[dict[str, Any]]
    result: SamplingResult
    coverage_summary: dict[str, Any]


def variant_to_candidate(variant: AudioVariant) -> SampleCandidate:
    return SampleCandidate(
        id=variant.id,
        sample_type=variant.sample_type,
        duration_sec=variant.duration_sec,
        metadata={
            "sample_type": variant.sample_type,
            "voice_source": variant.voice_source,
            "speaker_id": variant.speaker_id or "unknown",
            "gender": variant.gender,
            "age_group": variant.age_group,
            "volume": variant.volume,
            "pitch": variant.pitch,
            "speed": variant.speed,
            "noise_scene": variant.noise_scene,
            "impairment_type": variant.impairment_type,
            "variant_kind": variant.variant_kind,
            "snr_bucket": variant.snr_bucket or "unknown",
        },
    )


def metadata_snapshot(variant: AudioVariant) -> dict[str, Any]:
    return {
        "variant_id": variant.id,
        "source_id": variant.source_id,
        "stored_path": variant.stored_path,
        "text": variant.text,
        "normalized_text": variant.normalized_text,
        "sample_type": variant.sample_type,
        "voice_source": variant.voice_source,
        "speaker_id": variant.speaker_id,
        "gender": variant.gender,
        "age_group": variant.age_group,
        "volume": variant.volume,
        "pitch": variant.pitch,
        "speed": variant.speed,
        "noise_scene": variant.noise_scene,
        "impairment_type": variant.impairment_type,
        "variant_kind": variant.variant_kind,
        "duration_sec": variant.duration_sec,
    }


def matches_filters(variant: AudioVariant, filters: dict[str, Any]) -> bool:
    for field, allowed in filters.items():
        if field == "quality_status":
            continue
        value = getattr(variant, field)
        if value is None:
            value = "unknown"
        if value not in allowed:
            return False
    return True


def select_spec_samples(spec: DatasetSpec, session: Session) -> SpecSelection:
    ready_variants = session.exec(select(AudioVariant).where(AudioVariant.quality_status == "ready").order_by(AudioVariant.id)).all()
    overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec.id).order_by(ManualOverride.id)).all()
    include_ids = {item.variant_id for item in overrides if item.action == "include"}
    include_variants_by_id: dict[str, AudioVariant] = {}
    if include_ids:
        include_variants = session.exec(select(AudioVariant).where(AudioVariant.id.in_(include_ids)).order_by(AudioVariant.id)).all()
        include_variants_by_id = {item.id: item for item in include_variants}
        missing_include_ids = sorted(include_ids - set(include_variants_by_id))
        if missing_include_ids:
            raise ValueError(f"manual include variant not found: {', '.join(missing_include_ids)}")
        not_ready_include_ids = sorted(item.id for item in include_variants if item.quality_status != "ready")
        if not_ready_include_ids:
            raise ValueError(f"manual include variant must be ready: {', '.join(not_ready_include_ids)}")
        wrong_type_include_ids = sorted(item.id for item in include_variants if item.sample_type not in spec.quotas)
        if wrong_type_include_ids:
            raise ValueError(f"manual include sample_type must be in quotas: {', '.join(wrong_type_include_ids)}")

    auto_variants = [item for item in ready_variants if matches_filters(item, spec.filters)]
    if spec.min_duration_sec is not None:
        auto_variants = [item for item in auto_variants if item.duration_sec >= spec.min_duration_sec]
    if spec.max_duration_sec is not None:
        auto_variants = [item for item in auto_variants if item.duration_sec <= spec.max_duration_sec]
    auto_variants = [item for item in auto_variants if item.sample_type in spec.quotas]

    variants_by_id = {item.id: item for item in auto_variants}
    for item_id in sorted(include_variants_by_id):
        variants_by_id[item_id] = include_variants_by_id[item_id]
    variants = list(variants_by_id.values())
    candidates = [variant_to_candidate(item) for item in variants]
    result = sample_candidates(
        candidates=candidates,
        quotas=spec.quotas,
        balance_by=spec.balance_by,
        seed=spec.sampling_seed,
        overrides=[ManualOverrideInput(item.variant_id, item.action, item.reason) for item in overrides],
    )
    selected_by_id = {item.variant_id: item for item in result.items}
    selected_variants = [item for item in variants if item.id in selected_by_id]
    selected_variants.sort(key=lambda item: selected_by_id[item.id].selection_rank)
    snapshots = [metadata_snapshot(item) for item in selected_variants]
    coverage = build_coverage_summary(snapshots, spec.balance_by + ["sample_type"], result.shortfalls)
    return SpecSelection(
        variants=variants,
        selected_variants=selected_variants,
        selected_by_id=selected_by_id,
        overrides=overrides,
        snapshots=snapshots,
        result=result,
        coverage_summary=coverage,
    )
```

Create `/Users/e4/Documents/kws_testset/kws_testset/services/dataset_preview_service.py`:

```python
from __future__ import annotations

from typing import Any

from sqlmodel import Session

from kws_testset.models.dataset import DatasetSpec
from kws_testset.services.dataset_selection_service import select_spec_samples


def preview_spec_selection(spec: DatasetSpec, session: Session) -> dict[str, Any]:
    selection = select_spec_samples(spec, session)
    return {
        "spec_id": spec.id,
        "candidate_count": len(selection.variants),
        "item_count": len(selection.result.items),
        "counts_by_sample_type": selection.result.counts_by_sample_type,
        "shortfalls": selection.result.shortfalls,
        "coverage_summary": selection.coverage_summary,
    }
```

Modify `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py` so build uses the same service:

- Replace the local imports of `ManualOverrideInput`, `SampleCandidate`, and `sample_candidates` with:

```python
from kws_testset.services.dataset_selection_service import select_spec_samples
```

- Delete the local `_variant_to_candidate`, `_matches_filters`, and `_metadata_snapshot` helpers.

- In `build_dataset_version`, replace the block that builds `all_ready_variants`, `include_variants_by_id`, `auto_variants`, `candidates`, `result`, `selected_by_id`, and `selected_variants` with:

```python
        try:
            selection = select_spec_samples(spec, session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        overrides = selection.overrides
        selected_by_id = selection.selected_by_id
        selected_variants = selection.selected_variants
```

- Replace the later snapshot and coverage lines with:

```python
        snapshots_by_variant_id = {item["variant_id"]: item for item in selection.snapshots}
        snapshots = selection.snapshots
        coverage = selection.coverage_summary
```

- In `rules_snapshot`, keep the existing `overrides` list and set `shortfalls` from the shared result:

```python
                "shortfalls": selection.result.shortfalls,
```

- [ ] **Step 4: Add dataset browse and preview routes**

Modify `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`:

- Import the new service:

```python
from kws_testset.services.dataset_preview_service import preview_spec_selection
```

- Add payload helpers:

```python
def _spec_payload(spec: DatasetSpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "description": spec.description,
        "target_keyword": spec.target_keyword,
        "target_keyword_normalized": spec.target_keyword_normalized,
        "sampling_seed": spec.sampling_seed,
        "status": spec.status,
        "quotas": spec.quotas,
        "filters": spec.filters,
        "balance_by": spec.balance_by,
        "min_duration_sec": spec.min_duration_sec,
        "max_duration_sec": spec.max_duration_sec,
        "created_at": spec.created_at.isoformat(),
        "updated_at": spec.updated_at.isoformat(),
    }


def _version_payload(version: DatasetVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "dataset_spec_id": version.dataset_spec_id,
        "version": version.version,
        "name": version.name,
        "build_status": version.build_status,
        "sampling_seed": version.sampling_seed,
        "rules_snapshot": version.rules_snapshot,
        "coverage_summary": version.coverage_summary,
        "item_count": version.item_count,
        "total_duration_sec": version.total_duration_sec,
        "export_path": version.export_path,
        "created_at": version.created_at.isoformat(),
        "built_at": version.built_at.isoformat() if version.built_at else None,
        "exported_at": version.exported_at.isoformat() if version.exported_at else None,
    }


def _item_payload(item: DatasetItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "dataset_version_id": item.dataset_version_id,
        "variant_id": item.variant_id,
        "sample_type": item.sample_type,
        "text": item.text,
        "normalized_text": item.normalized_text,
        "duration_sec": item.duration_sec,
        "selection_reason": item.selection_reason,
        "selection_rank": item.selection_rank,
        "metadata_snapshot": item.metadata_snapshot,
    }
```

- Add routes:

```python
@router.get("/api/dataset-specs")
def list_dataset_specs(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        specs = session.exec(select(DatasetSpec).order_by(DatasetSpec.created_at.desc())).all()
    return {"items": [_spec_payload(spec) for spec in specs]}


@router.get("/api/dataset-specs/{spec_id}")
def get_dataset_spec(spec_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")
        overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec_id).order_by(ManualOverride.id)).all()
    payload = _spec_payload(spec)
    payload["overrides"] = [
        {"id": item.id, "variant_id": item.variant_id, "action": item.action, "reason": item.reason, "created_at": item.created_at.isoformat()}
        for item in overrides
    ]
    return payload


@router.post("/api/dataset-specs/{spec_id}/preview")
def preview_dataset_spec(spec_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset spec not found")
        _validate_filter_config(spec.filters)
        _validate_balance_by(spec.balance_by)
        try:
            return preview_spec_selection(spec, session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/dataset-versions")
def list_dataset_versions(request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        versions = session.exec(select(DatasetVersion).order_by(DatasetVersion.created_at.desc())).all()
    return {"items": [_version_payload(version) for version in versions]}


@router.get("/api/dataset-versions/{version_id}")
def get_dataset_version(version_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        version = session.get(DatasetVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="dataset version not found")
    return _version_payload(version)


@router.get("/api/dataset-versions/{version_id}/items")
def list_dataset_version_items(version_id: str, request: Request) -> dict[str, Any]:
    with Session(request.app.state.engine) as session:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="dataset version not found")
        items = session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == version_id).order_by(DatasetItem.selection_rank)).all()
    return {"items": [_item_payload(item) for item in items]}
```

- [ ] **Step 5: Run dataset tests and full backend tests**

Run:

```bash
uv run python -m pytest tests/test_dataset_browse_api.py tests/test_dataset_build_api.py -v
uv run python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add kws_testset/services/dataset_selection_service.py kws_testset/services/dataset_preview_service.py kws_testset/api/datasets.py tests/test_dataset_browse_api.py
git commit -m "feat: add dataset browse and preview APIs"
```

---

### Task 5: Frontend API Types, Client, Navigation, and Shared Components

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/App.tsx`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/styles.css`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/types/api.ts`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/api/client.ts`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/components/AudioPlayer.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/components/BulkEditToolbar.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/components/CoveragePanel.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/components/ErrorSummary.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/components/StatusBadge.tsx`
- Create initial page files that compile before their workflow logic is added:
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/DashboardPage.tsx`
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/ImportPage.tsx`
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/AssetsPage.tsx`
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/DatasetBuilderPage.tsx`
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/VersionsPage.tsx`
  - `/Users/e4/Documents/kws_testset/frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Run typecheck to establish frontend baseline**

Run:

```bash
cd frontend && npm run typecheck
```

Expected: PASS from Task 1 baseline. This is the baseline before adding typed API modules.

- [ ] **Step 2: Add TypeScript API types**

Create `/Users/e4/Documents/kws_testset/frontend/src/types/api.ts`:

```ts
export type ValidationPayload = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export type Taxonomy = Record<string, string[]>;

export type Asset = {
  id: string;
  source_id: string;
  stored_path: string;
  text: string;
  normalized_text: string;
  sample_type: string;
  quality_status: string;
  voice_source: string;
  speaker_id: string | null;
  gender: string;
  age_group: string;
  volume: string;
  pitch: string;
  speed: string;
  noise_scene: string;
  snr_bucket: string | null;
  impairment_type: string;
  variant_kind: string;
  duration_sec: number;
  sample_rate: number;
  channels: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  validation: ValidationPayload;
};

export type UploadRow = {
  path: string;
  original_filename: string;
  duration_sec: number;
  sample_rate: number;
  channels: number;
  bit_depth: number;
  sha256: string;
  status: string;
  error: string | null;
};

export type UploadResponse = {
  upload_id: string;
  uploaded: number;
  failed: number;
  files: UploadRow[];
};

export type ImportCommitFile = {
  path: string;
  text: string;
  sample_type: string;
  quality_status: string;
  voice_source: string;
  gender: string;
  age_group: string;
  volume: string;
  pitch: string;
  speed: string;
  noise_scene: string;
  impairment_type: string;
  notes?: string | null;
};

export type ImportBatch = {
  id: string;
  name: string;
  source_directory: string | null;
  file_count: number;
  imported_count: number;
  duplicate_count: number;
  failed_count?: number;
  status: string;
  created_at: string;
  completed_at: string | null;
  files?: Array<{ path: string; status: string; errors: string[] }>;
};

export type DatasetSpec = {
  id: string;
  name: string;
  description: string;
  target_keyword: string;
  target_keyword_normalized: string;
  sampling_seed: number;
  status: string;
  quotas: Record<string, number>;
  filters: Record<string, string[]>;
  balance_by: string[];
  min_duration_sec: number | null;
  max_duration_sec: number | null;
  created_at: string;
  updated_at: string;
  overrides?: ManualOverride[];
};

export type ManualOverride = {
  id: string;
  variant_id: string;
  action: string;
  reason: string;
  created_at: string;
};

export type DatasetPreview = {
  spec_id: string;
  candidate_count: number;
  item_count: number;
  counts_by_sample_type: Record<string, number>;
  shortfalls: Record<string, number>;
  coverage_summary: CoverageSummary;
};

export type CoverageSummary = {
  total: number;
  by_field?: Record<string, Record<string, number>>;
  shortfalls?: Record<string, number>;
};

export type DatasetVersion = {
  id: string;
  dataset_spec_id: string;
  version: number;
  name: string;
  build_status: string;
  sampling_seed: number;
  rules_snapshot: Record<string, unknown>;
  coverage_summary: CoverageSummary;
  item_count: number;
  total_duration_sec: number;
  export_path: string | null;
  created_at: string;
  built_at: string | null;
  exported_at: string | null;
};

export type DatasetItem = {
  id: string;
  dataset_version_id: string;
  variant_id: string;
  sample_type: string;
  text: string;
  normalized_text: string;
  duration_sec: number;
  selection_reason: string;
  selection_rank: number;
  metadata_snapshot: Record<string, unknown>;
};

export type ExportResponse = {
  export_dir: string;
  manifest: string;
  rich_manifest: string;
  dataset_yaml: string;
  coverage_summary: string;
  eval_config_snippet: string;
  negative_hours: number;
};
```

- [ ] **Step 3: Add API client**

Create `/Users/e4/Documents/kws_testset/frontend/src/api/client.ts`:

```ts
import type {
  Asset,
  DatasetItem,
  DatasetPreview,
  DatasetSpec,
  DatasetVersion,
  ExportResponse,
  ImportBatch,
  ImportCommitFile,
  Taxonomy,
  UploadResponse
} from '../types/api';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `API request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const contentType = response.headers.get('content-type') ?? '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body ? (body as { detail: unknown }).detail : body;
    throw new ApiError(response.status, detail);
  }
  return body as T;
}

export const api = {
  health: () => requestJson<{ status: string }>('/api/health'),
  taxonomy: () => requestJson<Taxonomy>('/api/taxonomy'),
  uploadWavs: (files: File[]) => {
    const form = new FormData();
    for (const file of files) form.append('files', file);
    return requestJson<UploadResponse>('/api/imports/uploads', { method: 'POST', body: form });
  },
  commitImport: (name: string, files: ImportCommitFile[]) =>
    requestJson<ImportBatch>('/api/imports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, partial: true, files })
    }),
  listImports: () => requestJson<{ items: ImportBatch[] }>('/api/imports'),
  listAssets: (params: Record<string, string> = {}) => {
    const search = new URLSearchParams(params);
    const query = search.toString();
    return requestJson<{ items: Asset[]; count: number; total: number; limit: number; offset: number }>(`/api/assets${query ? `?${query}` : ''}`);
  },
  patchAsset: (id: string, patch: Partial<Asset>) =>
    requestJson<{ asset: Asset }>('/api/assets/' + encodeURIComponent(id), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    }),
  bulkUpdateAssets: (assetIds: string[], patch: Record<string, unknown>) =>
    requestJson<{ updated: number; failed: number; results: Record<string, { ok: boolean; errors: string[]; warnings: string[] }> }>('/api/assets/bulk-update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset_ids: assetIds, patch })
    }),
  listDatasetSpecs: () => requestJson<{ items: DatasetSpec[] }>('/api/dataset-specs'),
  createDatasetSpec: (payload: {
    name: string;
    description: string;
    target_keyword: string;
    sampling_seed: number;
    quotas: Record<string, number>;
    filters: Record<string, string[]>;
    balance_by: string[];
    min_duration_sec?: number | null;
    max_duration_sec?: number | null;
  }) =>
    requestJson<{ id: string; name: string; quotas: Record<string, number> }>('/api/dataset-specs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  previewDatasetSpec: (id: string) => requestJson<DatasetPreview>(`/api/dataset-specs/${encodeURIComponent(id)}/preview`, { method: 'POST' }),
  buildDatasetSpec: (id: string) => requestJson<DatasetVersion>(`/api/dataset-specs/${encodeURIComponent(id)}/build`, { method: 'POST' }),
  listDatasetVersions: () => requestJson<{ items: DatasetVersion[] }>('/api/dataset-versions'),
  getDatasetVersionItems: (id: string) => requestJson<{ items: DatasetItem[] }>(`/api/dataset-versions/${encodeURIComponent(id)}/items`),
  exportDatasetVersion: (id: string) => requestJson<ExportResponse>(`/api/dataset-versions/${encodeURIComponent(id)}/export`, { method: 'POST' })
};
```

- [ ] **Step 4: Add shared components**

Create `/Users/e4/Documents/kws_testset/frontend/src/components/StatusBadge.tsx`:

```tsx
export function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status.replace(/[^a-z0-9_-]/gi, '-')}`}>{status}</span>;
}
```

Create `/Users/e4/Documents/kws_testset/frontend/src/components/ErrorSummary.tsx`:

```tsx
import { ApiError } from '../api/client';

function detailToLines(detail: unknown): string[] {
  if (typeof detail === 'string') return [detail];
  if (Array.isArray(detail)) return detail.map(String);
  if (detail && typeof detail === 'object' && 'errors' in detail) {
    const errors = (detail as { errors?: unknown }).errors;
    return Array.isArray(errors) ? errors.map(String) : [JSON.stringify(detail)];
  }
  return [JSON.stringify(detail)];
}

export function ErrorSummary({ error }: { error: unknown }) {
  if (!error) return null;
  const lines = error instanceof ApiError ? detailToLines(error.detail) : [error instanceof Error ? error.message : String(error)];
  return (
    <div className="error-summary">
      <strong>操作失败</strong>
      <ul>
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
```

Create `/Users/e4/Documents/kws_testset/frontend/src/components/AudioPlayer.tsx`:

```tsx
export function AudioPlayer({ assetId }: { assetId: string }) {
  return <audio controls preload="none" src={`/api/assets/${encodeURIComponent(assetId)}/audio`} className="audio-player" />;
}
```

Create `/Users/e4/Documents/kws_testset/frontend/src/components/CoveragePanel.tsx`:

```tsx
import type { CoverageSummary } from '../types/api';

export function CoveragePanel({ coverage }: { coverage: CoverageSummary | null }) {
  if (!coverage) return <p className="muted">暂无覆盖率数据。</p>;
  return (
    <div className="coverage-panel">
      <div className="metric-card">
        <span>Total</span>
        <strong>{coverage.total}</strong>
      </div>
      {coverage.shortfalls && Object.keys(coverage.shortfalls).length > 0 ? (
        <div className="warning-box">Shortfalls: {JSON.stringify(coverage.shortfalls)}</div>
      ) : null}
      {coverage.by_field
        ? Object.entries(coverage.by_field).map(([field, values]) => (
            <div className="coverage-field" key={field}>
              <h4>{field}</h4>
              <div className="tag-list">
                {Object.entries(values).map(([value, count]) => (
                  <span className="tag" key={`${field}-${value}`}>{value}: {count}</span>
                ))}
              </div>
            </div>
          ))
        : null}
    </div>
  );
}
```

Create `/Users/e4/Documents/kws_testset/frontend/src/components/BulkEditToolbar.tsx`:

```tsx
export function BulkEditToolbar({ selectedCount, onApply }: { selectedCount: number; onApply: (patch: Record<string, string>) => void }) {
  return (
    <div className="bulk-toolbar">
      <span>已选择 {selectedCount} 条</span>
      <button disabled={selectedCount === 0} onClick={() => onApply({ quality_status: 'ready' })}>标记 ready</button>
      <button disabled={selectedCount === 0} onClick={() => onApply({ noise_scene: 'clean' })}>noise=clean</button>
      <button disabled={selectedCount === 0} onClick={() => onApply({ volume: 'normal', pitch: 'normal', speed: 'normal' })}>音量/音调/语速 normal</button>
    </div>
  );
}
```

- [ ] **Step 5: Add page stubs and navigation**

Create each page with a non-empty, compiling component.

`/Users/e4/Documents/kws_testset/frontend/src/pages/DashboardPage.tsx`:

```tsx
export function DashboardPage() {
  return <section><h1>Dashboard</h1><p>资产状态和版本状态会在后续任务接入。</p></section>;
}
```

`/Users/e4/Documents/kws_testset/frontend/src/pages/ImportPage.tsx`:

```tsx
export function ImportPage() {
  return <section><h1>Import Wizard</h1><p>WAV 上传和 metadata 表格会在后续任务接入。</p></section>;
}
```

`/Users/e4/Documents/kws_testset/frontend/src/pages/AssetsPage.tsx`:

```tsx
export function AssetsPage() {
  return <section><h1>Assets</h1><p>资产列表、播放和编辑会在后续任务接入。</p></section>;
}
```

`/Users/e4/Documents/kws_testset/frontend/src/pages/DatasetBuilderPage.tsx`:

```tsx
export function DatasetBuilderPage() {
  return <section><h1>Dataset Builder</h1><p>spec 创建、preview 和 build 会在后续任务接入。</p></section>;
}
```

`/Users/e4/Documents/kws_testset/frontend/src/pages/VersionsPage.tsx`:

```tsx
export function VersionsPage() {
  return <section><h1>Versions / Export</h1><p>版本列表、items 和导出会在后续任务接入。</p></section>;
}
```

`/Users/e4/Documents/kws_testset/frontend/src/pages/SettingsPage.tsx`:

```tsx
export function SettingsPage() {
  return <section><h1>Settings</h1><p>taxonomy 和运行配置说明会在后续任务接入。</p></section>;
}
```

Replace `/Users/e4/Documents/kws_testset/frontend/src/App.tsx`:

```tsx
import { useState } from 'react';
import { AssetsPage } from './pages/AssetsPage';
import { DashboardPage } from './pages/DashboardPage';
import { DatasetBuilderPage } from './pages/DatasetBuilderPage';
import { ImportPage } from './pages/ImportPage';
import { SettingsPage } from './pages/SettingsPage';
import { VersionsPage } from './pages/VersionsPage';

type PageKey = 'dashboard' | 'import' | 'assets' | 'builder' | 'versions' | 'settings';

const pages: Array<{ key: PageKey; label: string }> = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'import', label: 'Import Wizard' },
  { key: 'assets', label: 'Assets' },
  { key: 'builder', label: 'Dataset Builder' },
  { key: 'versions', label: 'Versions / Export' },
  { key: 'settings', label: 'Settings' }
];

function renderPage(page: PageKey) {
  if (page === 'dashboard') return <DashboardPage />;
  if (page === 'import') return <ImportPage />;
  if (page === 'assets') return <AssetsPage />;
  if (page === 'builder') return <DatasetBuilderPage />;
  if (page === 'versions') return <VersionsPage />;
  return <SettingsPage />;
}

export function App() {
  const [page, setPage] = useState<PageKey>('dashboard');
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">Wake Testset</div>
        {pages.map((item) => (
          <button key={item.key} className={`nav-item ${page === item.key ? 'active' : ''}`} onClick={() => setPage(item.key)}>
            {item.label}
          </button>
        ))}
      </aside>
      <section className="content">{renderPage(page)}</section>
    </main>
  );
}
```

- [ ] **Step 6: Extend CSS**

Append to `/Users/e4/Documents/kws_testset/frontend/src/styles.css`:

```css
h1 { margin-top: 0; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.metric-card, .panel { background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 16px; }
.metric-card span { display: block; color: #94a3b8; font-size: 13px; }
.metric-card strong { display: block; margin-top: 8px; font-size: 28px; }
.toolbar, .bulk-toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }
button.primary, .toolbar button, .bulk-toolbar button { border: 0; border-radius: 10px; padding: 9px 12px; color: #fff; background: #2563eb; cursor: pointer; }
button:disabled { opacity: 0.45; cursor: not-allowed; }
input, select, textarea { border: 1px solid #334155; border-radius: 10px; padding: 8px 10px; color: #e5e7eb; background: #0f172a; }
table { width: 100%; border-collapse: collapse; background: #111827; border-radius: 14px; overflow: hidden; }
th, td { padding: 10px; border-bottom: 1px solid #1f2937; text-align: left; vertical-align: top; }
th { color: #cbd5e1; background: #1f2937; }
.muted { color: #94a3b8; }
.error-summary, .warning-box { border: 1px solid #92400e; border-radius: 12px; padding: 12px; background: #451a03; color: #fed7aa; margin: 12px 0; }
.status-badge { display: inline-flex; border-radius: 999px; padding: 3px 8px; font-size: 12px; background: #334155; color: #e5e7eb; }
.status-ready, .status-can_import { background: #065f46; color: #d1fae5; }
.status-draft { background: #78350f; color: #fde68a; }
.status-error, .status-invalid { background: #7f1d1d; color: #fecaca; }
.status-duplicate { background: #3730a3; color: #ddd6fe; }
.audio-player { max-width: 220px; width: 100%; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.tag { border-radius: 999px; padding: 4px 8px; background: #1f2937; color: #cbd5e1; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }
.form-grid label { display: flex; flex-direction: column; gap: 6px; color: #cbd5e1; }
```

- [ ] **Step 7: Run frontend checks**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands pass.

- [ ] **Step 8: Commit Task 5**

```bash
git add frontend/src
git commit -m "feat: add UI shell and API client"
```

---

### Task 6: Import Wizard and Assets Pages

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/ImportPage.tsx`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/AssetsPage.tsx`

- [ ] **Step 1: Replace ImportPage with upload, metadata table, and commit flow**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/ImportPage.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { ImportCommitFile, Taxonomy, UploadRow } from '../types/api';

type EditableRow = UploadRow & ImportCommitFile;

function defaultRow(row: UploadRow): EditableRow {
  return {
    ...row,
    path: row.path,
    text: '',
    sample_type: 'wake_positive',
    quality_status: 'draft',
    voice_source: 'human',
    gender: 'unknown',
    age_group: 'unknown',
    volume: 'normal',
    pitch: 'normal',
    speed: 'normal',
    noise_scene: 'clean',
    impairment_type: 'none',
    notes: null
  };
}

export function ImportPage() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [rows, setRows] = useState<EditableRow[]>([]);
  const [batchName, setBatchName] = useState('browser_import');
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
  }, []);

  async function upload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    setMessage('');
    const response = await api.uploadWavs(Array.from(files));
    setRows(response.files.map(defaultRow));
    setMessage(`上传完成：可处理 ${response.uploaded}，失败 ${response.failed}`);
  }

  function updateRow(index: number, patch: Partial<EditableRow>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  function bulkApply(patch: Partial<EditableRow>) {
    setRows((current) => current.map((row) => (row.status === 'can_import' ? { ...row, ...patch } : row)));
  }

  async function commit() {
    setError(null);
    const files = rows.filter((row) => row.status === 'can_import').map(({ original_filename, duration_sec, sample_rate, channels, bit_depth, sha256, status, error: rowError, ...file }) => file);
    const response = await api.commitImport(batchName, files);
    if (response.files) {
      const byPath = new Map(response.files.map((item) => [item.path, item]));
      setRows((current) => current.map((row) => {
        const result = byPath.get(row.path);
        if (!result || result.status !== 'error') return row;
        return { ...row, status: 'error', error: result.errors.join('; ') };
      }));
    }
    setMessage(`导入完成：${response.imported_count} 条，重复 ${response.duplicate_count} 条，失败 ${response.failed_count ?? 0} 条`);
  }

  const sampleTypes = taxonomy.sample_type ?? ['wake_positive', 'similar_negative', 'partial_wake', 'ordinary_negative'];
  const options = (key: string, fallback: string[]) => taxonomy[key] ?? fallback;

  return (
    <section>
      <h1>Import Wizard</h1>
      <ErrorSummary error={error} />
      {message ? <p className="warning-box">{message}</p> : null}
      <div className="toolbar">
        <input value={batchName} onChange={(event) => setBatchName(event.target.value)} aria-label="batch name" />
        <input type="file" accept=".wav,audio/wav" multiple onChange={(event) => upload(event.target.files).catch(setError)} />
        <button onClick={() => bulkApply({ text: '你好小智', sample_type: 'wake_positive' })}>批量正样本</button>
        <button onClick={() => bulkApply({ quality_status: 'ready' })}>批量 ready</button>
        <button className="primary" disabled={rows.filter((row) => row.status === 'can_import').length === 0} onClick={() => commit().catch(setError)}>提交导入</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>file</th><th>status</th><th>text</th><th>sample_type</th><th>quality</th><th>voice</th><th>gender</th><th>noise</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.path}-${index}`}>
              <td>{row.original_filename}<br /><span className="muted">{row.duration_sec.toFixed(2)}s</span></td>
              <td><StatusBadge status={row.status} />{row.error ? <div className="muted">{row.error}</div> : null}</td>
              <td><input value={row.text} onChange={(event) => updateRow(index, { text: event.target.value })} /></td>
              <td><select value={row.sample_type} onChange={(event) => updateRow(index, { sample_type: event.target.value })}>{sampleTypes.map((item) => <option key={item}>{item}</option>)}</select></td>
              <td><select value={row.quality_status} onChange={(event) => updateRow(index, { quality_status: event.target.value })}>{options('quality_status', ['draft', 'ready', 'deprecated']).map((item) => <option key={item}>{item}</option>)}</select></td>
              <td><select value={row.voice_source} onChange={(event) => updateRow(index, { voice_source: event.target.value })}>{options('voice_source', ['human', 'synthetic', 'unknown']).map((item) => <option key={item}>{item}</option>)}</select></td>
              <td><select value={row.gender} onChange={(event) => updateRow(index, { gender: event.target.value })}>{options('gender', ['male', 'female', 'unknown']).map((item) => <option key={item}>{item}</option>)}</select></td>
              <td><select value={row.noise_scene} onChange={(event) => updateRow(index, { noise_scene: event.target.value })}>{options('noise_scene', ['clean', 'home', 'office', 'unknown']).map((item) => <option key={item}>{item}</option>)}</select></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Replace AssetsPage with filtering, playback, single edit, and bulk edit**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/AssetsPage.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { AudioPlayer } from '../components/AudioPlayer';
import { BulkEditToolbar } from '../components/BulkEditToolbar';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { Asset, Taxonomy } from '../types/api';

export function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<unknown>(null);

  async function loadAssets(nextFilter = filter) {
    const params = nextFilter ? { sample_type: nextFilter } : {};
    const response = await api.listAssets(params);
    setAssets(response.items);
  }

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
    loadAssets('').catch(setError);
  }, []);

  function updateLocal(id: string, patch: Partial<Asset>) {
    setAssets((current) => current.map((asset) => (asset.id === id ? { ...asset, ...patch } : asset)));
  }

  async function save(asset: Asset) {
    const response = await api.patchAsset(asset.id, asset);
    setAssets((current) => current.map((item) => (item.id === asset.id ? response.asset : item)));
  }

  async function bulkApply(patch: Record<string, string>) {
    await api.bulkUpdateAssets(Array.from(selected), patch);
    setSelected(new Set());
    await loadAssets();
  }

  const sampleTypes = taxonomy.sample_type ?? ['wake_positive', 'similar_negative', 'partial_wake', 'ordinary_negative'];
  const qualityStatuses = taxonomy.quality_status ?? ['draft', 'ready', 'deprecated'];

  return (
    <section>
      <h1>Assets</h1>
      <ErrorSummary error={error} />
      <div className="toolbar">
        <select value={filter} onChange={(event) => { setFilter(event.target.value); loadAssets(event.target.value).catch(setError); }}>
          <option value="">all sample types</option>
          {sampleTypes.map((item) => <option key={item}>{item}</option>)}
        </select>
        <button onClick={() => loadAssets().catch(setError)}>刷新</button>
      </div>
      <BulkEditToolbar selectedCount={selected.size} onApply={(patch) => bulkApply(patch).catch(setError)} />
      <table>
        <thead><tr><th></th><th>audio</th><th>text</th><th>type</th><th>quality</th><th>voice/noise</th><th>validation</th><th>action</th></tr></thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id}>
              <td><input type="checkbox" checked={selected.has(asset.id)} onChange={(event) => setSelected((current) => { const next = new Set(current); event.target.checked ? next.add(asset.id) : next.delete(asset.id); return next; })} /></td>
              <td><AudioPlayer assetId={asset.id} /><div className="muted">{asset.duration_sec.toFixed(2)}s</div></td>
              <td><input value={asset.text} onChange={(event) => updateLocal(asset.id, { text: event.target.value })} /></td>
              <td><select value={asset.sample_type} onChange={(event) => updateLocal(asset.id, { sample_type: event.target.value })}>{sampleTypes.map((item) => <option key={item}>{item}</option>)}</select></td>
              <td><select value={asset.quality_status} onChange={(event) => updateLocal(asset.id, { quality_status: event.target.value })}>{qualityStatuses.map((item) => <option key={item}>{item}</option>)}</select></td>
              <td>{asset.voice_source}<br />{asset.noise_scene}</td>
              <td><StatusBadge status={asset.validation.ok ? asset.quality_status : 'invalid'} />{asset.validation.errors.map((line) => <div className="muted" key={line}>{line}</div>)}</td>
              <td><button onClick={() => save(asset).catch(setError)}>保存</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 3: Run frontend checks**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands pass.

- [ ] **Step 4: Run backend tests to ensure API compatibility remains intact**

Run:

```bash
uv run python -m pytest tests/test_upload_import_api.py tests/test_asset_edit_api.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 6**

```bash
git add frontend/src/pages/ImportPage.tsx frontend/src/pages/AssetsPage.tsx
git commit -m "feat: add import and asset management UI"
```

---

### Task 7: Dataset Builder and Versions / Export Pages

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/DatasetBuilderPage.tsx`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/VersionsPage.tsx`

- [ ] **Step 1: Replace DatasetBuilderPage with spec form, preview, and build flow**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/DatasetBuilderPage.tsx` with:

```tsx
import { useState } from 'react';
import { api } from '../api/client';
import { CoveragePanel } from '../components/CoveragePanel';
import { ErrorSummary } from '../components/ErrorSummary';
import type { DatasetPreview, DatasetVersion } from '../types/api';

export function DatasetBuilderPage() {
  const [name, setName] = useState('wakeword_regression');
  const [targetKeyword, setTargetKeyword] = useState('你好小智');
  const [positiveQuota, setPositiveQuota] = useState(10);
  const [similarQuota, setSimilarQuota] = useState(10);
  const [partialQuota, setPartialQuota] = useState(10);
  const [seed, setSeed] = useState(20260617);
  const [specId, setSpecId] = useState('');
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [built, setBuilt] = useState<DatasetVersion | null>(null);
  const [error, setError] = useState<unknown>(null);

  const quotas = {
    wake_positive: positiveQuota,
    similar_negative: similarQuota,
    partial_wake: partialQuota
  };

  async function createSpec() {
    setError(null);
    const response = await api.createDatasetSpec({
      name,
      description: 'Created from platform UI',
      target_keyword: targetKeyword,
      sampling_seed: seed,
      quotas,
      filters: { quality_status: ['ready'] },
      balance_by: ['sample_type', 'gender', 'noise_scene'],
      min_duration_sec: null,
      max_duration_sec: null
    });
    setSpecId(response.id);
    setPreview(null);
    setBuilt(null);
  }

  async function previewSpec() {
    if (!specId) return;
    setPreview(await api.previewDatasetSpec(specId));
  }

  async function buildSpec() {
    if (!specId) return;
    setBuilt(await api.buildDatasetSpec(specId));
  }

  return (
    <section>
      <h1>Dataset Builder</h1>
      <ErrorSummary error={error} />
      <div className="panel">
        <div className="form-grid">
          <label>name<input value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>target keyword<input value={targetKeyword} onChange={(event) => setTargetKeyword(event.target.value)} /></label>
          <label>seed<input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          <label>wake_positive<input type="number" value={positiveQuota} onChange={(event) => setPositiveQuota(Number(event.target.value))} /></label>
          <label>similar_negative<input type="number" value={similarQuota} onChange={(event) => setSimilarQuota(Number(event.target.value))} /></label>
          <label>partial_wake<input type="number" value={partialQuota} onChange={(event) => setPartialQuota(Number(event.target.value))} /></label>
        </div>
        <div className="toolbar">
          <button className="primary" onClick={() => createSpec().catch(setError)}>创建 spec</button>
          <button disabled={!specId} onClick={() => previewSpec().catch(setError)}>预览覆盖率</button>
          <button disabled={!specId} onClick={() => buildSpec().catch(setError)}>构建 version</button>
        </div>
        {specId ? <p className="muted">当前 spec: {specId}</p> : null}
      </div>
      {preview ? <CoveragePanel coverage={preview.coverage_summary} /> : null}
      {built ? <div className="warning-box">已构建：{built.name}，item_count={built.item_count}</div> : null}
    </section>
  );
}
```

- [ ] **Step 2: Replace VersionsPage with version list, item preview, and export flow**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/VersionsPage.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { CoveragePanel } from '../components/CoveragePanel';
import { ErrorSummary } from '../components/ErrorSummary';
import type { DatasetItem, DatasetVersion, ExportResponse } from '../types/api';

export function VersionsPage() {
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [selected, setSelected] = useState<DatasetVersion | null>(null);
  const [items, setItems] = useState<DatasetItem[]>([]);
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function load() {
    const response = await api.listDatasetVersions();
    setVersions(response.items);
  }

  async function selectVersion(version: DatasetVersion) {
    setSelected(version);
    setExportResult(null);
    const response = await api.getDatasetVersionItems(version.id);
    setItems(response.items);
  }

  async function exportVersion() {
    if (!selected) return;
    setExportResult(await api.exportDatasetVersion(selected.id));
    await load();
  }

  useEffect(() => {
    load().catch(setError);
  }, []);

  return (
    <section>
      <h1>Versions / Export</h1>
      <ErrorSummary error={error} />
      <div className="toolbar"><button onClick={() => load().catch(setError)}>刷新</button></div>
      <div className="card-grid">
        <div className="panel">
          <h2>Versions</h2>
          <table>
            <thead><tr><th>name</th><th>items</th><th>status</th><th>action</th></tr></thead>
            <tbody>{versions.map((version) => <tr key={version.id}><td>{version.name}</td><td>{version.item_count}</td><td>{version.build_status}</td><td><button onClick={() => selectVersion(version).catch(setError)}>查看</button></td></tr>)}</tbody>
          </table>
        </div>
        <div className="panel">
          <h2>Selected</h2>
          {selected ? <><p>{selected.name}</p><CoveragePanel coverage={selected.coverage_summary} /><button className="primary" onClick={() => exportVersion().catch(setError)}>导出</button></> : <p className="muted">请选择版本。</p>}
          {exportResult ? <div className="warning-box"><strong>导出完成</strong><br />{exportResult.export_dir}<br />negative_hours={exportResult.negative_hours}</div> : null}
        </div>
      </div>
      <div className="panel">
        <h2>Items</h2>
        <table>
          <thead><tr><th>rank</th><th>id</th><th>type</th><th>text</th><th>duration</th></tr></thead>
          <tbody>{items.map((item) => <tr key={item.id}><td>{item.selection_rank}</td><td>{item.id}</td><td>{item.sample_type}</td><td>{item.text}</td><td>{item.duration_sec.toFixed(2)}s</td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Run frontend checks**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands pass.

- [ ] **Step 4: Run dataset backend tests**

Run:

```bash
uv run python -m pytest tests/test_dataset_browse_api.py tests/test_dataset_build_api.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 7**

```bash
git add frontend/src/pages/DatasetBuilderPage.tsx frontend/src/pages/VersionsPage.tsx
git commit -m "feat: add dataset builder and export UI"
```

---

### Task 8: Dashboard, Settings, and README Run Instructions

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/DashboardPage.tsx`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/pages/SettingsPage.tsx`
- Modify: `/Users/e4/Documents/kws_testset/README.md`

- [ ] **Step 1: Replace DashboardPage with live summaries**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/DashboardPage.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import type { Asset, DatasetVersion } from '../types/api';

export function DashboardPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([api.listAssets(), api.listDatasetVersions()])
      .then(([assetResponse, versionResponse]) => {
        setAssets(assetResponse.items);
        setVersions(versionResponse.items);
      })
      .catch(setError);
  }, []);

  const ready = assets.filter((asset) => asset.quality_status === 'ready' && asset.validation.ok).length;
  const needsMetadata = assets.filter((asset) => !asset.validation.ok || asset.quality_status !== 'ready').length;
  const latest = versions[0] ?? null;

  return (
    <section>
      <h1>Dashboard</h1>
      <ErrorSummary error={error} />
      <div className="card-grid">
        <div className="metric-card"><span>Total Assets</span><strong>{assets.length}</strong></div>
        <div className="metric-card"><span>Ready</span><strong>{ready}</strong></div>
        <div className="metric-card"><span>Need Metadata</span><strong>{needsMetadata}</strong></div>
        <div className="metric-card"><span>Dataset Versions</span><strong>{versions.length}</strong></div>
      </div>
      <div className="panel">
        <h2>Latest Version</h2>
        {latest ? <p>{latest.name} · {latest.item_count} items · {latest.build_status}</p> : <p className="muted">暂无版本，请先创建 dataset spec 并构建。</p>}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Replace SettingsPage with taxonomy and runtime notes**

Replace `/Users/e4/Documents/kws_testset/frontend/src/pages/SettingsPage.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import type { Taxonomy } from '../types/api';

export function SettingsPage() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
  }, []);

  return (
    <section>
      <h1>Settings</h1>
      <ErrorSummary error={error} />
      <div className="panel">
        <h2>运行配置</h2>
        <p>后端配置来自 <code>configs/app.yaml</code>。数据目录、导出目录和目标关键词由后端读取，UI 第一版只展示说明，不直接修改配置文件。</p>
        <pre>uv run python -m kws_testset serve</pre>
      </div>
      <div className="panel">
        <h2>Taxonomy</h2>
        {Object.entries(taxonomy).map(([key, values]) => (
          <div className="coverage-field" key={key}>
            <h4>{key}</h4>
            <div className="tag-list">{values.map((value) => <span className="tag" key={`${key}-${value}`}>{value}</span>)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Update README with frontend commands**

Append to `/Users/e4/Documents/kws_testset/README.md`:

````markdown
## Frontend Development

The platform UI is a React + Vite + TypeScript app under `frontend/`.

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run backend and frontend in development mode:

```bash
uv run python -m kws_testset serve
cd frontend
npm run dev
```

Open the Vite URL printed by `npm run dev`. Vite proxies `/api` to `http://127.0.0.1:8000`.

Build the frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

After `frontend/dist` exists, FastAPI serves the built UI from:

```text
http://127.0.0.1:8000
```

These commands are the same on macOS, Windows, and Linux. Avoid relying on bash-only wrapper scripts for normal development.
````

- [ ] **Step 4: Run full frontend checks**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands pass.

- [ ] **Step 5: Commit Task 8**

```bash
git add README.md frontend/src/pages/DashboardPage.tsx frontend/src/pages/SettingsPage.tsx
git commit -m "feat: add dashboard settings and UI docs"
```

---

### Task 9: Final Verification and Cleanup

**Files:**
- Modify only if verification reveals a concrete failure.

- [ ] **Step 1: Run backend test suite**

Run:

```bash
uv run python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run doctor**

Run:

```bash
uv run python -m kws_testset doctor
```

Expected output includes:

```text
doctor=ok
```

- [ ] **Step 3: Run frontend typecheck and build**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands exit 0.

- [ ] **Step 4: Verify FastAPI can serve the built UI**

Run this one-off Python check:

```bash
uv run python - <<'PY'
from fastapi.testclient import TestClient
from kws_testset.app import create_app
client = TestClient(create_app())
root = client.get('/')
health = client.get('/api/health')
print(root.status_code, 'root_has_html=', '<html' in root.text.lower())
print(health.status_code, health.json())
assert root.status_code == 200
assert '<html' in root.text.lower()
assert health.status_code == 200
assert health.json() == {'status': 'ok'}
PY
```

Expected output includes:

```text
200 root_has_html= True
200 {'status': 'ok'}
```

- [ ] **Step 5: Verify git status and commit final verification note if changes were needed**

Run:

```bash
git status --short --branch
```

Expected: clean working tree. If verification required fixes, commit them with a focused message such as:

```bash
git add <changed-files>
git commit -m "fix: stabilize platform UI verification"
```

- [ ] **Step 6: Report completion with evidence**

Report the exact verification commands and their passing outputs. Include the current branch and latest commit hash.

---

## Plan Self-Review

Spec coverage:

- Browser multi-WAV upload and partial valid-row commit: Task 2 backend, Task 6 UI.
- Batch metadata editing during import: Task 6.
- Asset filtering, playback, single edit, bulk edit: Task 3 backend, Task 6 UI.
- Dataset spec creation, preview, build: Task 4 backend, Task 7 UI.
- Version listing, items, export: Task 4 backend, Task 7 UI.
- Dashboard: Task 8.
- Settings and taxonomy read-only display: Task 8.
- Cross-platform commands: Task 1 and Task 8 README.
- Minimum testing: Tasks 1-4 backend smoke, Tasks 5-8 frontend typecheck/build, Task 9 final verification.

No implementation task includes generation/enhancement jobs, evaluation result ingestion, dynamic taxonomy editing, multi-user workflows, or full E2E testing.
