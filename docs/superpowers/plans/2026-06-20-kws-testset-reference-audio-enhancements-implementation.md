# Reference Audio Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add concrete audio enhancement/degradation transforms inspired by the provided reference code to the existing TransformJob backend and Generation UI.

**Architecture:** Keep the existing synchronous TransformJob flow and AudioVariant lineage. Move DSP-heavy work from hand-written PCM loops to NumPy/SciPy helpers inside `audio_transform_service.py`, preserving deterministic `seed` behavior where randomization is used.

**Tech Stack:** Python 3.11, FastAPI, SQLModel, NumPy, SciPy, pytest, React/Vite/TypeScript.

---

### Task 1: Add DSP Transform Tests

**Files:**
- Create: `tests/test_audio_transform_service.py`
- Modify: `tests/test_transform_jobs_api.py`

- [x] **Step 1: Write failing service tests**

Add tests that create synthetic PCM16 WAVs and assert:
- `band_limit` reduces high-frequency FFT energy.
- `subband_eq` is deterministic with the same seed and changes the source.
- `narrowband` preserves sample rate and duration while changing samples.
- `amp_distortion` changes samples and remains valid PCM16.
- `amp_distortion` with `poly_distortion` changes samples.
- `spectral_mask` is deterministic with the same seed and changes the source.
- `signal_mimic` is deterministic with the same seed.

- [x] **Step 2: Write failing API test**

Add a TransformJob API test that posts `transform_kind=narrowband` and asserts a draft child variant is created with lineage and processing params.

- [x] **Step 3: Verify RED**

Run: `uv run python -m pytest tests/test_audio_transform_service.py tests/test_transform_jobs_api.py -v`

Expected: fails because new transform kinds are unknown and/or NumPy/SciPy are missing.

### Task 2: Implement NumPy/SciPy DSP Backend

**Files:**
- Modify: `pyproject.toml`
- Modify: `kws_testset/services/audio_transform_service.py`
- Modify: `uv.lock`

- [x] **Step 1: Add dependencies**

Add `numpy` and `scipy` to project dependencies, then run `uv sync --extra dev`.

- [x] **Step 2: Replace transform internals**

Read/write PCM16 through NumPy arrays while preserving existing `volume_gain`, `speed_change`, and `noise_mix` behavior. Add support for:
- `subband_eq`
- `band_limit`
- `narrowband`
- `spectral_mask`
- `amp_distortion`
- `signal_mimic`

- [x] **Step 3: Verify GREEN**

Run: `uv run python -m pytest tests/test_audio_transform_service.py tests/test_transform_jobs_api.py -v`

Expected: all targeted tests pass.

### Task 3: Expose New Transform Options In UI

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/pages/GenerationPage.tsx`

- [x] **Step 1: Extend frontend types**

Add the new transform kind string literals to `TransformKind`.

- [x] **Step 2: Add concise parameter controls**

Expose practical defaults and fields for each new transform kind:
- `subband_eq`: `seed`
- `band_limit`: `mode`, `cutoff_hz`, `seed`
- `narrowband`: `target_sample_rate`
- `spectral_mask`: `seed`
- `amp_distortion`: `distortion_type`, `rate`, `gain_db`
- `signal_mimic`: `seed`

- [x] **Step 3: Verify UI**

Run: `cd frontend && npm run typecheck && npm run build`

Expected: typecheck and build pass.

### Task 4: Full Verification And Commit

**Files:**
- Modify: all changed files from Tasks 1-3.

- [x] **Step 1: Run full backend verification**

Run: `uv run python -m pytest -v`

Expected: all backend tests pass.

- [x] **Step 2: Run doctor**

Run: `uv run python -m kws_testset doctor`

Expected: `doctor=ok`.

- [x] **Step 3: Commit**

Run:

```bash
git add README.md pyproject.toml uv.lock kws_testset/services/audio_transform_service.py tests/test_audio_transform_service.py tests/test_transform_jobs_api.py frontend/src/types/api.ts frontend/src/pages/GenerationPage.tsx docs/superpowers/plans/2026-06-20-kws-testset-reference-audio-enhancements-implementation.md
git commit -m "feat: add reference audio enhancement transforms"
```
