# KWS Testset Generation Enhancement C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first C-loop MVP for audio enhancement: select existing variants, create transform jobs, generate child WAV variants, record lineage/parameters, and expose a small UI for batch generation.

**Architecture:** Keep the platform local and synchronous for this phase. A new `TransformJob` table records requested inputs, transform kind, parameters, per-row results, and created variant IDs. The service writes generated WAV files to `data/library/variants/`, creates draft `AudioVariant` children with `parent_variant_id`, `variant_kind`, `processing_params`, and `impairment_chain`, then the existing Assets UI remains the place to inspect and mark generated variants ready.

**Tech Stack:** Python 3.11 standard `wave`/`struct`/`random`, FastAPI, SQLModel, pytest, React 18, Vite, TypeScript.

---

## Scope Check

This implements the C MVP from the platform design docs:

- `parent_variant_id`, `variant_kind`, `processing_params`, and `impairment_chain` are populated for generated variants.
- New WAV files are generated under `data/library/variants/`.
- Users can batch-generate variants from existing assets and then review them in Assets.

Explicitly out of scope:

- TTS generation.
- Background queues, cancellation, retry workers, or async job processing.
- External DSP libraries.
- D evaluation ingestion/analysis.
- Full Playwright E2E.

## File Structure

Backend:

- Create: `/Users/e4/Documents/kws_testset/kws_testset/models/transform_job.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/models/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/audio_transform_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/transform_job_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/transforms.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_transform_jobs_api.py`

Frontend:

- Modify: `/Users/e4/Documents/kws_testset/frontend/src/types/api.ts`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/api/client.ts`
- Modify: `/Users/e4/Documents/kws_testset/frontend/src/App.tsx`
- Create: `/Users/e4/Documents/kws_testset/frontend/src/pages/GenerationPage.tsx`

Docs:

- Modify: `/Users/e4/Documents/kws_testset/README.md`

## Task 1: Backend Transform Job API

- [ ] **Step 1: Write failing tests**

Create `/Users/e4/Documents/kws_testset/tests/test_transform_jobs_api.py` with tests for:

- `POST /api/transform-jobs` rejects unknown transform kind with HTTP 400.
- `POST /api/transform-jobs` with `volume_gain` creates a completed job and one child `AudioVariant`.
- The child variant is a draft, references `parent_variant_id`, has `variant_kind=volume_gain`, stores generated audio under `library/variants`, has a different sha256 from the parent, and records `processing_params`.
- `GET /api/transform-jobs` and `GET /api/transform-jobs/{id}` return the job.
- Missing input variant IDs are reported as per-row failures instead of aborting the whole job.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
uv run python -m pytest tests/test_transform_jobs_api.py -v
```

Expected: fail because `/api/transform-jobs` does not exist.

- [ ] **Step 3: Add model and service implementation**

Implement:

- `TransformJob` SQLModel with job status, transform kind, input IDs, params, result rows, created IDs, counts, timestamps, and optional error.
- `audio_transform_service.py` with deterministic local transforms:
  - `volume_gain` using `gain_db`.
  - `speed_change` using `speed_factor`.
  - `noise_mix` using `snr_db` and optional `seed`.
- `transform_job_service.py` to validate input, run transforms synchronously, write files to `data/library/variants/`, create draft child variants, and record per-input results.

- [ ] **Step 4: Add API router**

Implement:

```text
GET  /api/transform-jobs
POST /api/transform-jobs
GET  /api/transform-jobs/{job_id}
```

Include the router in `kws_testset/app.py`.

- [ ] **Step 5: Verify backend tests**

Run:

```bash
uv run python -m pytest tests/test_transform_jobs_api.py -v
uv run python -m pytest tests/test_asset_edit_api.py tests/test_dataset_build_api.py -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit backend**

```bash
git add kws_testset/models/transform_job.py kws_testset/models/__init__.py kws_testset/services/audio_transform_service.py kws_testset/services/transform_job_service.py kws_testset/api/transforms.py kws_testset/app.py tests/test_transform_jobs_api.py
git commit -m "feat: add transform job backend"
```

## Task 2: Generation UI

- [ ] **Step 1: Add frontend types and API client functions**

Extend `frontend/src/types/api.ts` with:

- `TransformKind`
- `TransformJobResult`
- `TransformJob`
- `CreateTransformJobRequest`

Extend `frontend/src/api/client.ts` with:

- `listTransformJobs()`
- `createTransformJob(payload)`
- `getTransformJob(id)`

- [ ] **Step 2: Create GenerationPage**

Create `/Users/e4/Documents/kws_testset/frontend/src/pages/GenerationPage.tsx`:

- List assets with checkboxes.
- Let the user choose transform kind.
- Show parameter controls for `volume_gain`, `speed_change`, and `noise_mix`.
- Submit selected variants to `POST /api/transform-jobs`.
- Show latest job counts, per-row failures, and created variant IDs.
- Show recent transform jobs.

- [ ] **Step 3: Add navigation**

Modify `frontend/src/App.tsx` to add a `Generation` page between Assets and Dataset Builder.

- [ ] **Step 4: Verify frontend**

Run:

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both commands pass.

- [ ] **Step 5: Commit frontend**

```bash
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/App.tsx frontend/src/pages/GenerationPage.tsx
git commit -m "feat: add generation UI"
```

## Task 3: Docs and Final Verification

- [ ] **Step 1: Update README**

Add a short section describing C-loop generation support, supported transform kinds, and the fact that generated variants start as draft for review.

- [ ] **Step 2: Run final verification**

Run:

```bash
uv run python -m pytest -v
uv run python -m kws_testset doctor
cd frontend && npm run typecheck && npm run build
```

Also verify static serving:

```bash
uv run python -c "from fastapi.testclient import TestClient; from kws_testset.app import create_app; client = TestClient(create_app()); root = client.get('/'); health = client.get('/api/health'); print(root.status_code, 'root_has_html=', '<html' in root.text.lower()); print(health.status_code, health.json()); assert root.status_code == 200; assert '<html' in root.text.lower(); assert health.status_code == 200; assert health.json() == {'status': 'ok'}"
```

- [ ] **Step 3: Commit docs/fixes**

If README or verification fixes changed files:

```bash
git add README.md <changed-files>
git commit -m "docs: document generation enhancement flow"
```

## Self-Review

- Spec coverage: Implements docs C flow: select variant, create enhancement task, generate WAV, create child `AudioVariant`, populate processing params, return generated variants to Assets for review.
- Scope: Does not implement D, TTS, background queue, or external audio libraries.
- TDD: Backend behavior starts with failing API tests. Frontend is verified with TypeScript and production build.
- Cross-platform: Uses `pathlib.Path` and Python standard library WAV processing; no shell-only runtime path.
