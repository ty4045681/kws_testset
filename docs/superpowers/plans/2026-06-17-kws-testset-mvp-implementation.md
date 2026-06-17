# KWS Testset Platform MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform, locally runnable MVP that can import WAV metadata, manage ready audio variants, build versioned KWS testsets with include/exclude overrides, and export sherpa_eval-compatible manifests.

**Architecture:** Implement a backend-first Python package with FastAPI, SQLite/SQLModel, Typer CLI, and a minimal static web shell served by FastAPI. Keep the first UI lightweight so the project runs on macOS, Windows, and Linux without Node; a richer React UI can replace the shell without changing backend APIs.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, Typer, PyYAML, pytest, pathlib, standard-library wave/hashlib/json/csv-style file handling.

---

## Scope Check

The approved design covers import, asset management, dataset construction, export, future generation/enhancement, and future evaluation analysis. This plan implements the first runnable MVP only:

- Included: config, CLI, doctor command, SQLite schema, taxonomy, text normalization, WAV probe/hash, import service, asset API, ready validation, dataset spec/version build, sampling, coverage summary, export, minimum tests, minimal static web shell.
- Excluded from this plan: full React/Vite frontend, TTS/enhancement jobs, model evaluation ingestion, multi-user workflows, cloud storage, and platform-internal model evaluation.

This produces working software on its own and preserves the data model boundaries needed for later phases.

## File Structure

Create this structure under `/Users/e4/Documents/kws_testset`:

```text
/Users/e4/Documents/kws_testset/
├── pyproject.toml
├── README.md
├── configs/
│   └── app.yaml
├── kws_testset/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── cli.py
│   ├── config.py
│   ├── db.py
│   ├── taxonomy.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── assets.py
│   │   ├── datasets.py
│   │   ├── imports.py
│   │   └── taxonomy.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── audio.py
│   │   ├── dataset.py
│   │   └── import_batch.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_probe.py
│   │   ├── coverage_service.py
│   │   ├── export_service.py
│   │   ├── import_service.py
│   │   ├── sampling_service.py
│   │   ├── text_normalize.py
│   │   └── validation_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── hashing.py
│   │   └── ids.py
│   └── web/
│       └── index.html
└── tests/
    ├── conftest.py
    ├── test_audio_probe.py
    ├── test_export_service.py
    ├── test_sampling_service.py
    ├── test_smoke.py
    ├── test_text_normalize.py
    └── test_validation_service.py
```

Responsibilities:

- `kws_testset/config.py`: load cross-platform YAML config and resolve paths with `pathlib.Path`.
- `kws_testset/db.py`: create SQLite engine/session and initialize tables.
- `kws_testset/taxonomy.py`: enum values used by APIs, UI, and validators.
- `kws_testset/models/*`: SQLModel database tables.
- `kws_testset/services/*`: pure business logic for probing, normalization, validation, import, sampling, coverage, and export.
- `kws_testset/api/*`: FastAPI routers with thin request/response logic.
- `kws_testset/web/index.html`: minimal static web shell for a runnable local platform.
- `tests/*`: minimum backend tests only.

---

### Task 1: Project Packaging, Config, CLI, and Doctor Command

**Files:**
- Create: `/Users/e4/Documents/kws_testset/pyproject.toml`
- Create: `/Users/e4/Documents/kws_testset/README.md`
- Create: `/Users/e4/Documents/kws_testset/configs/app.yaml`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/__main__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/config.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/cli.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

Create `/Users/e4/Documents/kws_testset/tests/test_smoke.py`:

```python
from pathlib import Path

from kws_testset.config import AppConfig, load_config


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_smoke.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'kws_testset'` or missing `load_config`.

- [ ] **Step 3: Add packaging and default config**

Create `/Users/e4/Documents/kws_testset/pyproject.toml`:

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
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "httpx>=0.27.0",
]

[project.scripts]
kws-testset = "kws_testset.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `/Users/e4/Documents/kws_testset/README.md`:

```markdown
# KWS Testset Platform

Local MVP for building and exporting keyword wake-word testsets.
```

Create `/Users/e4/Documents/kws_testset/configs/app.yaml`:

```yaml
app:
  data_dir: data
  target_keyword: 你好小智

export:
  default_audio_mode: reference_original_path

eval_project:
  root: ""
  manifest_dir: sherpa_eval/data
```

Create `/Users/e4/Documents/kws_testset/kws_testset/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `/Users/e4/Documents/kws_testset/kws_testset/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppSection:
    data_dir: Path
    target_keyword: str


@dataclass(frozen=True)
class ExportSection:
    default_audio_mode: str


@dataclass(frozen=True)
class EvalProjectSection:
    root: Path | None
    manifest_dir: Path


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    app: AppSection
    export: ExportSection
    eval_project: EvalProjectSection


def _resolve_path(raw: str | Path | None, base_dir: Path) -> Path | None:
    if raw is None:
        return None
    value = Path(str(raw)).expanduser()
    if str(value) == "":
        return None
    if value.is_absolute():
        return value
    return base_dir / value


def load_config(path: str | Path = "configs/app.yaml") -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    base_dir = config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent
    raw: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        raw = loaded or {}

    app_raw = raw.get("app", {})
    export_raw = raw.get("export", {})
    eval_raw = raw.get("eval_project", {})

    data_dir = _resolve_path(app_raw.get("data_dir", "data"), base_dir)
    if data_dir is None:
        data_dir = base_dir / "data"

    return AppConfig(
        config_path=config_path,
        app=AppSection(
            data_dir=data_dir,
            target_keyword=str(app_raw.get("target_keyword", "你好小智")),
        ),
        export=ExportSection(
            default_audio_mode=str(export_raw.get("default_audio_mode", "reference_original_path")),
        ),
        eval_project=EvalProjectSection(
            root=_resolve_path(eval_raw.get("root", ""), base_dir),
            manifest_dir=Path(str(eval_raw.get("manifest_dir", "sherpa_eval/data"))),
        ),
    )
```

Create `/Users/e4/Documents/kws_testset/kws_testset/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer

from kws_testset.config import load_config

app = typer.Typer(help="KWS testset platform CLI")


@app.command()
def doctor(config: Path = typer.Option(Path("configs/app.yaml"), help="Config path")) -> None:
    cfg = load_config(config)
    cfg.app.data_dir.mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "library" / "sources").mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "library" / "variants").mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "exports").mkdir(parents=True, exist_ok=True)
    typer.echo(f"config={cfg.config_path}")
    typer.echo(f"data_dir={cfg.app.data_dir}")
    typer.echo(f"target_keyword={cfg.app.target_keyword}")
    typer.echo("doctor=ok")


@app.command()
def serve(
    config: Path = typer.Option(Path("configs/app.yaml"), help="Config path"),
    host: str = typer.Option("127.0.0.1", help="Host"),
    port: int = typer.Option(8000, help="Port"),
) -> None:
    import uvicorn

    from kws_testset.app import create_app

    fastapi_app = create_app(config_path=config)
    uvicorn.run(fastapi_app, host=host, port=port)
```

Create `/Users/e4/Documents/kws_testset/kws_testset/__main__.py`:

```python
from kws_testset.cli import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run:

```bash
uv sync --extra dev
uv run pytest tests/test_smoke.py -v
```

Expected: PASS.

- [ ] **Step 5: Run doctor**

Run:

```bash
uv run kws-testset doctor
```

Expected output includes:

```text
doctor=ok
```

- [ ] **Step 6: Commit Task 1**

```bash
git add pyproject.toml README.md configs/app.yaml kws_testset/__init__.py kws_testset/__main__.py kws_testset/config.py kws_testset/cli.py tests/test_smoke.py
git commit -m "feat: add project scaffold and doctor command"
```

---

### Task 2: Taxonomy, Text Normalization, and Semantic Validation

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/taxonomy.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/text_normalize.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/validation_service.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_text_normalize.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_validation_service.py`

- [ ] **Step 1: Write failing normalization tests**

Create `/Users/e4/Documents/kws_testset/tests/test_text_normalize.py`:

```python
from kws_testset.services.text_normalize import contains_keyword, normalize_text


def test_normalize_chinese_keeps_text_and_trims_spaces():
    assert normalize_text("  你好小智  ") == "你好小智"


def test_normalize_english_uppercases_and_uses_underscore():
    assert normalize_text(" hello   xiao zhi ") == "HELLO_XIAO_ZHI"


def test_contains_keyword_uses_normalized_forms():
    assert contains_keyword(" hello   xiao zhi ", "HELLO XIAO ZHI") is True
```

- [ ] **Step 2: Write failing semantic validation tests**

Create `/Users/e4/Documents/kws_testset/tests/test_validation_service.py`:

```python
from kws_testset.services.validation_service import validate_sample_semantics


def test_wake_positive_requires_keyword():
    result = validate_sample_semantics("你好小智", "wake_positive", "你好小智")
    assert result.ok is True
    assert result.errors == []


def test_wake_positive_rejects_missing_keyword():
    result = validate_sample_semantics("你好小志", "wake_positive", "你好小智")
    assert result.ok is False
    assert "wake_positive text must contain target keyword" in result.errors


def test_negative_types_reject_complete_keyword():
    for sample_type in ["similar_negative", "partial_wake", "ordinary_negative"]:
        result = validate_sample_semantics("你好小智", sample_type, "你好小智")
        assert result.ok is False
        assert f"{sample_type} text must not contain target keyword" in result.errors
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_text_normalize.py tests/test_validation_service.py -v
```

Expected: FAIL with missing modules or functions.

- [ ] **Step 4: Implement taxonomy and text normalization**

Create `/Users/e4/Documents/kws_testset/kws_testset/taxonomy.py`:

```python
from __future__ import annotations

SAMPLE_TYPES = ["wake_positive", "similar_negative", "partial_wake", "ordinary_negative"]
VOICE_SOURCES = ["human", "synthetic", "unknown"]
GENDERS = ["male", "female", "unknown"]
AGE_GROUPS = ["child", "teen", "adult", "elderly", "unknown"]
VOLUMES = ["low", "normal", "high", "unknown"]
PITCHES = ["low", "normal", "high", "unknown"]
SPEEDS = ["slow", "normal", "fast", "unknown"]
NOISE_SCENES = ["clean", "home", "office", "car", "street", "music", "babble", "other", "unknown"]
IMPAIRMENT_TYPES = ["none", "device_denoise", "network_denoise", "codec", "far_field", "clipping", "other", "unknown"]
QUALITY_STATUSES = ["draft", "ready", "deprecated"]
VARIANT_KINDS = ["original", "speed_change", "pitch_shift", "volume_gain", "noise_mix", "device_denoise", "network_denoise", "codec", "far_field", "clipping", "combined", "other"]


def as_dict() -> dict[str, list[str]]:
    return {
        "sample_type": SAMPLE_TYPES,
        "voice_source": VOICE_SOURCES,
        "gender": GENDERS,
        "age_group": AGE_GROUPS,
        "volume": VOLUMES,
        "pitch": PITCHES,
        "speed": SPEEDS,
        "noise_scene": NOISE_SCENES,
        "impairment_type": IMPAIRMENT_TYPES,
        "quality_status": QUALITY_STATUSES,
        "variant_kind": VARIANT_KINDS,
    }
```

Create `/Users/e4/Documents/kws_testset/kws_testset/services/__init__.py`:

```python
__all__: list[str] = []
```

Create `/Users/e4/Documents/kws_testset/kws_testset/services/text_normalize.py`:

```python
from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str, *, upper: bool = True, space_to_underscore: bool = True) -> str:
    value = unicodedata.normalize("NFKC", text or "").strip()
    value = re.sub(r"\s+", " ", value)
    if upper:
        value = value.upper()
    if space_to_underscore:
        value = value.replace(" ", "_")
    return value


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)
    return normalized_keyword != "" and normalized_keyword in normalized_text
```

- [ ] **Step 5: Implement semantic validation**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/validation_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kws_testset.taxonomy import SAMPLE_TYPES
from kws_testset.services.text_normalize import contains_keyword


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_sample_semantics(text: str, sample_type: str, target_keyword: str) -> ValidationResult:
    errors: list[str] = []
    if sample_type not in SAMPLE_TYPES:
        errors.append(f"unknown sample_type: {sample_type}")
        return ValidationResult(ok=False, errors=errors, warnings=[])

    has_keyword = contains_keyword(text, target_keyword)
    if sample_type == "wake_positive" and not has_keyword:
        errors.append("wake_positive text must contain target keyword")
    if sample_type in {"similar_negative", "partial_wake", "ordinary_negative"} and has_keyword:
        errors.append(f"{sample_type} text must not contain target keyword")
    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=[])


def validate_file_exists(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(ok=False, errors=[f"file does not exist: {path}"], warnings=[])
    if not path.is_file():
        return ValidationResult(ok=False, errors=[f"path is not a file: {path}"], warnings=[])
    return ValidationResult(ok=True, errors=[], warnings=[])
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_text_normalize.py tests/test_validation_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add kws_testset/taxonomy.py kws_testset/services/__init__.py kws_testset/services/text_normalize.py kws_testset/services/validation_service.py tests/test_text_normalize.py tests/test_validation_service.py
git commit -m "feat: add taxonomy and semantic validation"
```

---

### Task 3: WAV Probe and Hash Utilities

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/utils/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/utils/hashing.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/audio_probe.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_audio_probe.py`

- [ ] **Step 1: Write failing WAV probe test**

Create `/Users/e4/Documents/kws_testset/tests/test_audio_probe.py`:

```python
from pathlib import Path
import math
import wave

from kws_testset.services.audio_probe import probe_wav
from kws_testset.utils.hashing import sha256_file


def write_silent_wav(path: Path, sample_rate: int = 16000, seconds: float = 0.25) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)


def test_probe_wav_reads_duration_sample_rate_channels_and_hash(tmp_path: Path):
    wav_path = tmp_path / "sample.wav"
    write_silent_wav(wav_path)

    info = probe_wav(wav_path)

    assert info.path == wav_path
    assert math.isclose(info.duration_sec, 0.25, abs_tol=0.01)
    assert info.sample_rate == 16000
    assert info.channels == 1
    assert info.bit_depth == 16
    assert info.sha256 == sha256_file(wav_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_audio_probe.py -v
```

Expected: FAIL with missing `probe_wav` or `sha256_file`.

- [ ] **Step 3: Implement hashing utility**

Create `/Users/e4/Documents/kws_testset/kws_testset/utils/__init__.py`:

```python
__all__: list[str] = []
```

Create `/Users/e4/Documents/kws_testset/kws_testset/utils/hashing.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Implement WAV probe**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/audio_probe.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import wave

from kws_testset.utils.hashing import sha256_file


@dataclass(frozen=True)
class AudioProbe:
    path: Path
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str


def probe_wav(path: str | Path) -> AudioProbe:
    wav_path = Path(path).expanduser().resolve()
    with wave.open(str(wav_path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frame_count = wav.getnframes()
    duration_sec = frame_count / float(sample_rate)
    return AudioProbe(
        path=wav_path,
        duration_sec=duration_sec,
        sample_rate=sample_rate,
        channels=channels,
        bit_depth=sample_width * 8,
        sha256=sha256_file(wav_path),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_audio_probe.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add kws_testset/utils/__init__.py kws_testset/utils/hashing.py kws_testset/services/audio_probe.py tests/test_audio_probe.py
git commit -m "feat: add wav probe and hashing"
```

---

### Task 4: SQLite Schema and Database Initialization

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/db.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/models/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/models/audio.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/models/import_batch.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/models/dataset.py`
- Modify: `/Users/e4/Documents/kws_testset/tests/test_smoke.py`

- [ ] **Step 1: Extend smoke test for database initialization**

Modify `/Users/e4/Documents/kws_testset/tests/test_smoke.py` by adding:

```python
from sqlmodel import Session, select

from kws_testset.db import create_engine_for_config, init_db
from kws_testset.models.audio import AudioSource


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
```

- [ ] **Step 2: Run smoke test to verify it fails**

Run:

```bash
uv run pytest tests/test_smoke.py -v
```

Expected: FAIL with missing `db` or models.

- [ ] **Step 3: Implement database models**

Create `/Users/e4/Documents/kws_testset/kws_testset/models/audio.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioSource(SQLModel, table=True):
    id: str = Field(primary_key=True)
    original_filename: str
    stored_path: str
    sha256: str = Field(index=True, unique=True)
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int | None = None
    import_batch_id: str | None = Field(default=None, index=True)
    imported_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class AudioVariant(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source_id: str = Field(index=True)
    parent_variant_id: str | None = Field(default=None, index=True)
    variant_kind: str = Field(default="original", index=True)
    stored_path: str
    sha256: str = Field(index=True, unique=True)
    duration_sec: float
    sample_rate: int
    channels: int
    text: str = ""
    normalized_text: str = ""
    sample_type: str = "ordinary_negative"
    quality_status: str = Field(default="draft", index=True)
    voice_source: str = "unknown"
    speaker_id: str | None = None
    gender: str = "unknown"
    age_group: str = "unknown"
    timbre_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    volume: str = "unknown"
    pitch: str = "unknown"
    speed: str = "unknown"
    noise_scene: str = "unknown"
    snr_bucket: str | None = None
    impairment_type: str = "none"
    impairment_chain: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    processing_params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    custom_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

Create `/Users/e4/Documents/kws_testset/kws_testset/models/import_batch.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from kws_testset.models.audio import utc_now


class ImportBatch(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    source_directory: str | None = None
    file_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    status: str = "draft"
    default_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
```

Create `/Users/e4/Documents/kws_testset/kws_testset/models/dataset.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from kws_testset.models.audio import utc_now


class DatasetSpec(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    target_keyword: str
    target_keyword_normalized: str
    sampling_seed: int = 20260617
    status: str = "active"
    quotas: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    filters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    balance_by: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    min_duration_sec: float | None = None
    max_duration_sec: float | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ManualOverride(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_spec_id: str = Field(index=True)
    variant_id: str = Field(index=True)
    action: str
    reason: str
    created_at: datetime = Field(default_factory=utc_now)


class DatasetVersion(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_spec_id: str = Field(index=True)
    version: int
    name: str
    build_status: str = "built"
    sampling_seed: int
    rules_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    coverage_summary: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    item_count: int = 0
    total_duration_sec: float = 0.0
    export_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    built_at: datetime | None = None
    exported_at: datetime | None = None


class DatasetItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_version_id: str = Field(index=True)
    variant_id: str = Field(index=True)
    sample_type: str = Field(index=True)
    text: str
    normalized_text: str
    duration_sec: float
    selection_reason: str
    selection_rank: int
    metadata_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
```

Create `/Users/e4/Documents/kws_testset/kws_testset/models/__init__.py`:

```python
from kws_testset.models.audio import AudioSource, AudioVariant
from kws_testset.models.dataset import DatasetItem, DatasetSpec, DatasetVersion, ManualOverride
from kws_testset.models.import_batch import ImportBatch

__all__ = [
    "AudioSource",
    "AudioVariant",
    "DatasetItem",
    "DatasetSpec",
    "DatasetVersion",
    "ImportBatch",
    "ManualOverride",
]
```

- [ ] **Step 4: Implement database initialization**

Create `/Users/e4/Documents/kws_testset/kws_testset/db.py`:

```python
from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, create_engine
from sqlalchemy.engine import Engine

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
```

- [ ] **Step 5: Run smoke test to verify it passes**

Run:

```bash
uv run pytest tests/test_smoke.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add kws_testset/db.py kws_testset/models tests/test_smoke.py
git commit -m "feat: add sqlite schema"
```

---

### Task 5: Import Service and Import API

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/utils/ids.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/__init__.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Create: `/Users/e4/Documents/kws_testset/tests/conftest.py`

- [ ] **Step 1: Create API test fixture**

Create `/Users/e4/Documents/kws_testset/tests/conftest.py`:

```python
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
            wav.writeframes(b"\x00\x00" * frames)
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
```

- [ ] **Step 2: Write failing import API test**

Add this test to `/Users/e4/Documents/kws_testset/tests/test_smoke.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_smoke.py::test_import_scan_endpoint_returns_wav_metadata -v
```

Expected: FAIL with missing `kws_testset.app` or route.

- [ ] **Step 4: Implement IDs and import scan service**

Create `/Users/e4/Documents/kws_testset/kws_testset/utils/ids.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def short_hash(value: str, length: int = 12) -> str:
    return value[:length]


def dated_id(prefix: str, hash_value: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{stamp}_{short_hash(hash_value)}"


def new_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{stamp}_{uuid4().hex[:12]}"
```

Create `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from kws_testset.models.audio import AudioSource
from kws_testset.services.audio_probe import probe_wav


@dataclass(frozen=True)
class ScannedAudioFile:
    path: Path
    original_filename: str
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int
    sha256: str
    status: str


def _expand_wav_inputs(paths: list[str]) -> list[Path]:
    expanded: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if path.is_dir():
            expanded.extend(sorted(path.rglob("*.wav")))
        else:
            expanded.append(path)
    return expanded


def scan_wav_paths(paths: list[str], session: Session) -> list[ScannedAudioFile]:
    results: list[ScannedAudioFile] = []
    for path in _expand_wav_inputs(paths):
        probe = probe_wav(path)
        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        status = "duplicate" if existing else "can_import"
        results.append(
            ScannedAudioFile(
                path=probe.path,
                original_filename=probe.path.name,
                duration_sec=probe.duration_sec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                bit_depth=probe.bit_depth,
                sha256=probe.sha256,
                status=status,
            )
        )
    return results
```

- [ ] **Step 5: Implement FastAPI app and import route**

Create `/Users/e4/Documents/kws_testset/kws_testset/api/__init__.py`:

```python
__all__: list[str] = []
```

Create `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py`:

```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlmodel import Session

from kws_testset.services.import_service import scan_wav_paths

router = APIRouter(prefix="/api/imports", tags=["imports"])


class ScanRequest(BaseModel):
    paths: list[str]


@router.post("/scan")
def scan_imports(payload: ScanRequest, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        files = scan_wav_paths(payload.paths, session)
    return {
        "scanned": len(files),
        "files": [
            {
                "path": str(item.path),
                "original_filename": item.original_filename,
                "duration_sec": item.duration_sec,
                "sample_rate": item.sample_rate,
                "channels": item.channels,
                "bit_depth": item.bit_depth,
                "sha256": item.sha256,
                "status": item.status,
            }
            for item in files
        ],
    }
```

Create `/Users/e4/Documents/kws_testset/kws_testset/app.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from kws_testset.api.imports import router as imports_router
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

    app.include_router(imports_router)
    return app
```

- [ ] **Step 6: Run import API test to verify it passes**

Run:

```bash
uv run pytest tests/test_smoke.py::test_import_scan_endpoint_returns_wav_metadata -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add kws_testset/utils/ids.py kws_testset/services/import_service.py kws_testset/api/__init__.py kws_testset/api/imports.py kws_testset/app.py tests/conftest.py tests/test_smoke.py
git commit -m "feat: add import scanning api"
```

---

### Task 6: Create Import Commit Flow and Asset API

**Files:**
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/assets.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_import_and_assets.py`

- [ ] **Step 1: Write failing import commit and asset list test**

Create `/Users/e4/Documents/kws_testset/tests/test_import_and_assets.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_import_and_assets.py -v
```

Expected: FAIL because `POST /api/imports` and `GET /api/assets` are missing.

- [ ] **Step 3: Implement import commit service**

Append to `/Users/e4/Documents/kws_testset/kws_testset/services/import_service.py`:

```python
from datetime import datetime, timezone
import shutil
from typing import Any

from kws_testset.config import AppConfig
from kws_testset.models.audio import AudioVariant
from kws_testset.models.import_batch import ImportBatch
from kws_testset.services.text_normalize import normalize_text
from kws_testset.services.validation_service import validate_sample_semantics
from kws_testset.utils.ids import dated_id, new_id


def commit_import_batch(name: str, files: list[dict[str, Any]], config: AppConfig, session: Session) -> ImportBatch:
    batch_id = new_id("imp")
    batch = ImportBatch(id=batch_id, name=name, file_count=len(files), status="imported")
    session.add(batch)

    source_root = config.app.data_dir / "library" / "sources"
    source_root.mkdir(parents=True, exist_ok=True)

    imported_count = 0
    duplicate_count = 0
    for item in files:
        probe = probe_wav(item["path"])
        existing = session.exec(select(AudioSource).where(AudioSource.sha256 == probe.sha256)).first()
        if existing:
            duplicate_count += 1
            continue

        semantic = validate_sample_semantics(item["text"], item["sample_type"], config.app.target_keyword)
        if not semantic.ok:
            raise ValueError("; ".join(semantic.errors))

        source_id = dated_id("src", probe.sha256)
        variant_id = dated_id("var", probe.sha256)
        stored_path = source_root / f"{source_id}.wav"
        shutil.copy2(probe.path, stored_path)

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

    batch.imported_count = imported_count
    batch.duplicate_count = duplicate_count
    batch.completed_at = datetime.now(timezone.utc)
    session.add(batch)
    session.commit()
    session.refresh(batch)
    return batch
```

- [ ] **Step 4: Implement import commit API**

Modify `/Users/e4/Documents/kws_testset/kws_testset/api/imports.py` by adding request models and route:

```python
class ImportFileRequest(BaseModel):
    path: str
    text: str
    sample_type: str
    quality_status: str = "draft"
    voice_source: str = "unknown"
    gender: str = "unknown"
    age_group: str = "unknown"
    volume: str = "unknown"
    pitch: str = "unknown"
    speed: str = "unknown"
    noise_scene: str = "unknown"
    impairment_type: str = "none"
    notes: str | None = None


class CommitImportRequest(BaseModel):
    name: str
    files: list[ImportFileRequest]


@router.post("")
def commit_import(payload: CommitImportRequest, request: Request) -> dict[str, Any]:
    from kws_testset.services.import_service import commit_import_batch

    engine = request.app.state.engine
    config = request.app.state.config
    with Session(engine) as session:
        batch = commit_import_batch(
            name=payload.name,
            files=[item.model_dump() for item in payload.files],
            config=config,
            session=session,
        )
    return {
        "id": batch.id,
        "name": batch.name,
        "imported_count": batch.imported_count,
        "duplicate_count": batch.duplicate_count,
        "status": batch.status,
    }
```

- [ ] **Step 5: Implement asset list API**

Create `/Users/e4/Documents/kws_testset/kws_testset/api/assets.py`:

```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
def list_assets(request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        variants = session.exec(select(AudioVariant).order_by(AudioVariant.created_at)).all()
    return {
        "items": [
            {
                "id": item.id,
                "source_id": item.source_id,
                "stored_path": item.stored_path,
                "text": item.text,
                "normalized_text": item.normalized_text,
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
                "duration_sec": item.duration_sec,
            }
            for item in variants
        ]
    }
```

Modify `/Users/e4/Documents/kws_testset/kws_testset/app.py` to include assets router:

```python
from kws_testset.api.assets import router as assets_router
```

and inside `create_app` before `return app`:

```python
    app.include_router(assets_router)
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_import_and_assets.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

```bash
git add kws_testset/services/import_service.py kws_testset/api/imports.py kws_testset/api/assets.py kws_testset/app.py tests/test_import_and_assets.py
git commit -m "feat: add import commit and asset api"
```

---

### Task 7: Sampling and Coverage Services

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/sampling_service.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/coverage_service.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_sampling_service.py`

- [ ] **Step 1: Write failing sampling tests**

Create `/Users/e4/Documents/kws_testset/tests/test_sampling_service.py`:

```python
from kws_testset.services.sampling_service import ManualOverrideInput, SampleCandidate, sample_candidates


def candidate(idx: int, sample_type: str, gender: str = "female", noise_scene: str = "clean") -> SampleCandidate:
    return SampleCandidate(
        id=f"var_{idx}",
        sample_type=sample_type,
        duration_sec=1.0,
        metadata={
            "voice_source": "human",
            "gender": gender,
            "age_group": "adult",
            "noise_scene": noise_scene,
            "impairment_type": "none",
        },
    )


def test_sampling_respects_quota_exclude_include_and_seed():
    candidates = [
        candidate(1, "wake_positive", "female", "clean"),
        candidate(2, "wake_positive", "male", "clean"),
        candidate(3, "wake_positive", "female", "car"),
        candidate(4, "wake_positive", "male", "car"),
    ]
    overrides = [
        ManualOverrideInput(variant_id="var_1", action="exclude", reason="bad audio"),
        ManualOverrideInput(variant_id="var_4", action="include", reason="regression anchor"),
    ]

    result = sample_candidates(
        candidates=candidates,
        quotas={"wake_positive": 2},
        balance_by=["gender", "noise_scene"],
        seed=123,
        overrides=overrides,
    )
    result_again = sample_candidates(
        candidates=candidates,
        quotas={"wake_positive": 2},
        balance_by=["gender", "noise_scene"],
        seed=123,
        overrides=overrides,
    )

    assert [item.variant_id for item in result.items] == [item.variant_id for item in result_again.items]
    assert "var_1" not in [item.variant_id for item in result.items]
    assert "var_4" in [item.variant_id for item in result.items]
    assert result.counts_by_sample_type["wake_positive"] == 2
    assert result.shortfalls == {}


def test_sampling_reports_shortfall_without_backfilling_other_types():
    candidates = [candidate(1, "similar_negative")]

    result = sample_candidates(
        candidates=candidates,
        quotas={"similar_negative": 3, "wake_positive": 2},
        balance_by=["gender"],
        seed=123,
        overrides=[],
    )

    assert result.counts_by_sample_type["similar_negative"] == 1
    assert result.shortfalls == {"similar_negative": 2, "wake_positive": 2}
```

- [ ] **Step 2: Run sampling tests to verify they fail**

Run:

```bash
uv run pytest tests/test_sampling_service.py -v
```

Expected: FAIL with missing sampling service.

- [ ] **Step 3: Implement sampling service**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/sampling_service.py`:

```python
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class SampleCandidate:
    id: str
    sample_type: str
    duration_sec: float
    metadata: dict[str, str]


@dataclass(frozen=True)
class ManualOverrideInput:
    variant_id: str
    action: str
    reason: str


@dataclass(frozen=True)
class SelectedSample:
    variant_id: str
    sample_type: str
    selection_reason: str
    selection_rank: int


@dataclass(frozen=True)
class SamplingResult:
    items: list[SelectedSample]
    counts_by_sample_type: dict[str, int]
    shortfalls: dict[str, int]


def _bucket_key(candidate: SampleCandidate, balance_by: list[str]) -> tuple[str, ...]:
    return tuple(candidate.metadata.get(field, "unknown") for field in balance_by)


def _round_robin(candidates: list[SampleCandidate], needed: int, balance_by: list[str], seed: int) -> list[SampleCandidate]:
    buckets: dict[tuple[str, ...], list[SampleCandidate]] = defaultdict(list)
    for item in candidates:
        buckets[_bucket_key(item, balance_by)].append(item)

    rng = random.Random(seed)
    queues: list[deque[SampleCandidate]] = []
    for key in sorted(buckets):
        values = list(buckets[key])
        rng.shuffle(values)
        queues.append(deque(values))

    selected: list[SampleCandidate] = []
    while queues and len(selected) < needed:
        next_queues: list[deque[SampleCandidate]] = []
        for queue in queues:
            if len(selected) >= needed:
                next_queues.append(queue)
                continue
            if queue:
                selected.append(queue.popleft())
            if queue:
                next_queues.append(queue)
        queues = next_queues
    return selected


def sample_candidates(
    candidates: list[SampleCandidate],
    quotas: dict[str, int],
    balance_by: list[str],
    seed: int,
    overrides: list[ManualOverrideInput],
) -> SamplingResult:
    excluded = {item.variant_id for item in overrides if item.action == "exclude"}
    included = {item.variant_id for item in overrides if item.action == "include"}
    by_id = {item.id: item for item in candidates}

    selected: list[SelectedSample] = []
    rank = 1
    counts: dict[str, int] = {sample_type: 0 for sample_type in quotas}
    shortfalls: dict[str, int] = {}

    for sample_type in sorted(quotas):
        quota = quotas[sample_type]
        type_candidates = [item for item in candidates if item.sample_type == sample_type and item.id not in excluded]
        manual_items = [item for item_id, item in by_id.items() if item_id in included and item.sample_type == sample_type and item.id not in excluded]
        manual_items = sorted(manual_items, key=lambda item: item.id)

        for item in manual_items[:quota]:
            selected.append(SelectedSample(item.id, sample_type, "manual_include", rank))
            rank += 1
        remaining = max(0, quota - len(manual_items[:quota]))
        manual_ids = {item.id for item in manual_items}
        auto_pool = [item for item in type_candidates if item.id not in manual_ids]
        auto_items = _round_robin(auto_pool, remaining, balance_by, seed)
        for item in auto_items:
            selected.append(SelectedSample(item.id, sample_type, "auto", rank))
            rank += 1

        count = len(manual_items[:quota]) + len(auto_items)
        counts[sample_type] = count
        if count < quota:
            shortfalls[sample_type] = quota - count

    return SamplingResult(items=selected, counts_by_sample_type=counts, shortfalls=shortfalls)
```

- [ ] **Step 4: Implement coverage helper**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/coverage_service.py`:

```python
from __future__ import annotations

from collections import Counter
from typing import Any


def count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter = Counter(str(item.get(field, "unknown")) for item in items)
    return dict(sorted(counter.items()))


def build_coverage_summary(items: list[dict[str, Any]], fields: list[str], shortfalls: dict[str, int]) -> dict[str, Any]:
    return {
        "total": len(items),
        "shortfalls": shortfalls,
        "by_field": {field: count_by_field(items, field) for field in fields},
    }
```

- [ ] **Step 5: Run sampling tests to verify they pass**

Run:

```bash
uv run pytest tests/test_sampling_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 7**

```bash
git add kws_testset/services/sampling_service.py kws_testset/services/coverage_service.py tests/test_sampling_service.py
git commit -m "feat: add reproducible dataset sampling"
```

---

### Task 8: Dataset Spec, Overrides, Build API, and Version Snapshot

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_dataset_build_api.py`

- [ ] **Step 1: Write failing dataset build API test**

Create `/Users/e4/Documents/kws_testset/tests/test_dataset_build_api.py`:

```python
def import_asset(client, wav_factory, name, text, sample_type):
    wav_path = wav_factory(name)
    response = client.post(
        "/api/imports",
        json={
            "name": f"batch_{name}",
            "files": [
                {
                    "path": str(wav_path),
                    "text": text,
                    "sample_type": sample_type,
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


def test_create_spec_and_build_version(client, wav_factory):
    import_asset(client, wav_factory, "pos.wav", "你好小智", "wake_positive")
    import_asset(client, wav_factory, "neg.wav", "你好小志", "similar_negative")

    spec_response = client.post(
        "/api/dataset-specs",
        json={
            "name": "wakeword_regression",
            "description": "main regression set",
            "target_keyword": "你好小智",
            "sampling_seed": 7,
            "quotas": {"wake_positive": 1, "similar_negative": 1},
            "filters": {"quality_status": ["ready"]},
            "balance_by": ["gender", "noise_scene"],
            "min_duration_sec": 0.01,
            "max_duration_sec": 5.0,
        },
    )
    assert spec_response.status_code == 200
    spec_id = spec_response.json()["id"]

    build_response = client.post(f"/api/dataset-specs/{spec_id}/build")

    assert build_response.status_code == 200
    payload = build_response.json()
    assert payload["item_count"] == 2
    assert payload["version"] == 1
    assert payload["coverage_summary"]["total"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_dataset_build_api.py -v
```

Expected: FAIL because dataset routes are missing.

- [ ] **Step 3: Implement dataset routes and build logic**

Create `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from kws_testset.models.audio import AudioVariant
from kws_testset.models.dataset import DatasetItem, DatasetSpec, DatasetVersion, ManualOverride
from kws_testset.services.coverage_service import build_coverage_summary
from kws_testset.services.sampling_service import ManualOverrideInput, SampleCandidate, sample_candidates
from kws_testset.services.text_normalize import normalize_text
from kws_testset.utils.ids import dated_id, new_id

router = APIRouter(tags=["datasets"])


class DatasetSpecRequest(BaseModel):
    name: str
    description: str = ""
    target_keyword: str
    sampling_seed: int = 20260617
    quotas: dict[str, int]
    filters: dict[str, Any] = {}
    balance_by: list[str] = []
    min_duration_sec: float | None = None
    max_duration_sec: float | None = None


class OverrideRequest(BaseModel):
    variant_id: str
    action: str
    reason: str


def _variant_to_candidate(variant: AudioVariant) -> SampleCandidate:
    return SampleCandidate(
        id=variant.id,
        sample_type=variant.sample_type,
        duration_sec=variant.duration_sec,
        metadata={
            "voice_source": variant.voice_source,
            "gender": variant.gender,
            "age_group": variant.age_group,
            "volume": variant.volume,
            "pitch": variant.pitch,
            "speed": variant.speed,
            "noise_scene": variant.noise_scene,
            "impairment_type": variant.impairment_type,
        },
    )


def _matches_filters(variant: AudioVariant, filters: dict[str, Any]) -> bool:
    for field, allowed in filters.items():
        if field == "quality_status":
            continue
        if not isinstance(allowed, list):
            continue
        value = getattr(variant, field, None)
        if value not in allowed:
            return False
    return True


def _metadata_snapshot(variant: AudioVariant) -> dict[str, Any]:
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


@router.post("/api/dataset-specs")
def create_dataset_spec(payload: DatasetSpecRequest, request: Request) -> dict[str, Any]:
    spec_id = new_id("ds")
    spec = DatasetSpec(
        id=spec_id,
        name=payload.name,
        description=payload.description,
        target_keyword=payload.target_keyword,
        target_keyword_normalized=normalize_text(payload.target_keyword),
        sampling_seed=payload.sampling_seed,
        quotas=payload.quotas,
        filters=payload.filters,
        balance_by=payload.balance_by,
        min_duration_sec=payload.min_duration_sec,
        max_duration_sec=payload.max_duration_sec,
    )
    with Session(request.app.state.engine) as session:
        session.add(spec)
        session.commit()
        session.refresh(spec)
    return {"id": spec.id, "name": spec.name, "quotas": spec.quotas}


@router.post("/api/dataset-specs/{spec_id}/overrides")
def create_manual_override(spec_id: str, payload: OverrideRequest, request: Request) -> dict[str, Any]:
    if payload.action not in {"include", "exclude"}:
        return {"error": "action must be include or exclude"}
    override = ManualOverride(
        id=new_id("ovr"),
        dataset_spec_id=spec_id,
        variant_id=payload.variant_id,
        action=payload.action,
        reason=payload.reason,
    )
    with Session(request.app.state.engine) as session:
        session.add(override)
        session.commit()
        session.refresh(override)
    return {"id": override.id, "dataset_spec_id": override.dataset_spec_id, "variant_id": override.variant_id, "action": override.action, "reason": override.reason}


@router.post("/api/dataset-specs/{spec_id}/build")
def build_dataset_version(spec_id: str, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    with Session(engine) as session:
        spec = session.get(DatasetSpec, spec_id)
        if spec is None:
            return {"error": "dataset spec not found"}

        variants = session.exec(select(AudioVariant)).all()
        variants = [item for item in variants if item.quality_status == "ready"]
        variants = [item for item in variants if _matches_filters(item, spec.filters)]
        if spec.min_duration_sec is not None:
            variants = [item for item in variants if item.duration_sec >= spec.min_duration_sec]
        if spec.max_duration_sec is not None:
            variants = [item for item in variants if item.duration_sec <= spec.max_duration_sec]
        variants = [item for item in variants if item.sample_type in spec.quotas]

        overrides = session.exec(select(ManualOverride).where(ManualOverride.dataset_spec_id == spec_id)).all()
        candidates = [_variant_to_candidate(item) for item in variants]
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

        existing_versions = session.exec(select(DatasetVersion).where(DatasetVersion.dataset_spec_id == spec_id)).all()
        version_number = len(existing_versions) + 1
        version_id = f"dsv_{spec.name}_v{version_number:03d}"
        snapshots = [_metadata_snapshot(item) for item in selected_variants]
        coverage = build_coverage_summary(snapshots, spec.balance_by + ["sample_type"], result.shortfalls)
        version = DatasetVersion(
            id=version_id,
            dataset_spec_id=spec.id,
            version=version_number,
            name=f"{spec.name}_v{version_number:03d}",
            sampling_seed=spec.sampling_seed,
            rules_snapshot={
                "quotas": spec.quotas,
                "filters": spec.filters,
                "balance_by": spec.balance_by,
            },
            coverage_summary=coverage,
            item_count=len(selected_variants),
            total_duration_sec=sum(item.duration_sec for item in selected_variants),
            built_at=datetime.now(timezone.utc),
        )
        session.add(version)
        for variant in selected_variants:
            selected = selected_by_id[variant.id]
            item = DatasetItem(
                id=f"utt_{spec.name}_v{version_number:03d}_{selected.selection_rank:06d}",
                dataset_version_id=version.id,
                variant_id=variant.id,
                sample_type=variant.sample_type,
                text=variant.text,
                normalized_text=variant.normalized_text,
                duration_sec=variant.duration_sec,
                selection_reason=selected.selection_reason,
                selection_rank=selected.selection_rank,
                metadata_snapshot=_metadata_snapshot(variant),
            )
            session.add(item)
        session.commit()
        session.refresh(version)

    return {
        "id": version.id,
        "name": version.name,
        "version": version.version,
        "item_count": version.item_count,
        "total_duration_sec": version.total_duration_sec,
        "coverage_summary": version.coverage_summary,
    }
```

Modify `/Users/e4/Documents/kws_testset/kws_testset/app.py` to include dataset router:

```python
from kws_testset.api.datasets import router as datasets_router
```

inside `create_app` before `return app`:

```python
    app.include_router(datasets_router)
```

- [ ] **Step 4: Run dataset build API test to verify it passes**

Run:

```bash
uv run pytest tests/test_dataset_build_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 8**

```bash
git add kws_testset/api/datasets.py kws_testset/app.py tests/test_dataset_build_api.py
git commit -m "feat: add dataset build api"
```

---

### Task 9: Export Service and Export API

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/services/export_service.py`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`
- Create: `/Users/e4/Documents/kws_testset/tests/test_export_service.py`

- [ ] **Step 1: Write failing export service test**

Create `/Users/e4/Documents/kws_testset/tests/test_export_service.py`:

```python
import json
from pathlib import Path

from kws_testset.services.export_service import ExportItem, export_dataset


def test_export_dataset_writes_manifest_dataset_yaml_and_negative_hours(tmp_path: Path):
    items = [
        ExportItem(
            id="utt_001",
            audio="/abs/pos.wav",
            text="你好小智",
            duration=1.0,
            sample_type="wake_positive",
            metadata={"sample_type": "wake_positive", "gender": "female"},
        ),
        ExportItem(
            id="utt_002",
            audio="/abs/neg.wav",
            text="你好小志",
            duration=3.6,
            sample_type="similar_negative",
            metadata={"sample_type": "similar_negative", "gender": "male"},
        ),
    ]

    result = export_dataset(
        export_dir=tmp_path / "exports" / "wakeword_regression" / "v001",
        dataset_name="wakeword_regression",
        version=1,
        target_keyword="你好小智",
        sampling_seed=7,
        items=items,
        coverage_summary={"total": 2},
    )

    manifest_lines = (result.export_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(manifest_lines[0]) == {"id": "utt_001", "audio": "/abs/pos.wav", "text": "你好小智", "duration": 1.0}
    assert (result.export_dir / "rich_manifest.jsonl").exists()
    assert (result.export_dir / "dataset.yaml").exists()
    assert "negative_hours: 0.001" in (result.export_dir / "dataset.yaml").read_text(encoding="utf-8")
    assert "wakeword_regression_v001" in (result.export_dir / "eval_config_snippet.yaml").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run export test to verify it fails**

Run:

```bash
uv run pytest tests/test_export_service.py -v
```

Expected: FAIL with missing export service.

- [ ] **Step 3: Implement export service**

Create `/Users/e4/Documents/kws_testset/kws_testset/services/export_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import yaml


NEGATIVE_SAMPLE_TYPES = {"similar_negative", "partial_wake", "ordinary_negative"}


@dataclass(frozen=True)
class ExportItem:
    id: str
    audio: str
    text: str
    duration: float
    sample_type: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExportResult:
    export_dir: Path
    manifest_path: Path
    rich_manifest_path: Path
    dataset_yaml_path: Path
    coverage_summary_path: Path
    eval_config_snippet_path: Path
    negative_hours: float


def export_dataset(
    export_dir: Path,
    dataset_name: str,
    version: int,
    target_keyword: str,
    sampling_seed: int,
    items: list[ExportItem],
    coverage_summary: dict[str, Any],
) -> ExportResult:
    export_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = export_dir / "manifest.jsonl"
    rich_manifest_path = export_dir / "rich_manifest.jsonl"
    dataset_yaml_path = export_dir / "dataset.yaml"
    coverage_summary_path = export_dir / "coverage_summary.json"
    eval_config_snippet_path = export_dir / "eval_config_snippet.yaml"

    with manifest_path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            file_obj.write(json.dumps({"id": item.id, "audio": item.audio, "text": item.text, "duration": item.duration}, ensure_ascii=False) + "\n")

    with rich_manifest_path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            row = {"id": item.id, "audio": item.audio, "text": item.text, "duration": item.duration, **item.metadata}
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")

    coverage_summary_path.write_text(json.dumps(coverage_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    negative_duration = sum(item.duration for item in items if item.sample_type in NEGATIVE_SAMPLE_TYPES)
    negative_hours = round(negative_duration / 3600.0, 3)
    version_name = f"{dataset_name}_v{version:03d}"
    dataset_yaml = {
        "dataset": {
            "name": dataset_name,
            "version": version,
            "id": version_name,
            "target_keyword": target_keyword,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "sampling_seed": sampling_seed,
        },
        "counts": {
            "total": len(items),
            "total_duration_sec": round(sum(item.duration for item in items), 3),
            "negative_duration_sec": round(negative_duration, 3),
            "negative_hours": negative_hours,
        },
        "files": {
            "manifest": "manifest.jsonl",
            "rich_manifest": "rich_manifest.jsonl",
            "coverage_summary": "coverage_summary.json",
        },
    }
    dataset_yaml_path.write_text(yaml.safe_dump(dataset_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8")

    eval_snippet = {
        "eval": {
            "testsets": [{"name": version_name, "manifest": str(manifest_path.resolve())}],
            "negative_hours": {version_name: negative_hours},
        }
    }
    eval_config_snippet_path.write_text(yaml.safe_dump(eval_snippet, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return ExportResult(
        export_dir=export_dir,
        manifest_path=manifest_path,
        rich_manifest_path=rich_manifest_path,
        dataset_yaml_path=dataset_yaml_path,
        coverage_summary_path=coverage_summary_path,
        eval_config_snippet_path=eval_config_snippet_path,
        negative_hours=negative_hours,
    )
```

- [ ] **Step 4: Run export service test to verify it passes**

Run:

```bash
uv run pytest tests/test_export_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Add dataset version export route**

Append to `/Users/e4/Documents/kws_testset/kws_testset/api/datasets.py`:

```python
@router.post("/api/dataset-versions/{version_id}/export")
def export_dataset_version(version_id: str, request: Request) -> dict[str, Any]:
    from kws_testset.services.export_service import ExportItem, export_dataset

    engine = request.app.state.engine
    config = request.app.state.config
    with Session(engine) as session:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            return {"error": "dataset version not found"}
        spec = session.get(DatasetSpec, version.dataset_spec_id)
        if spec is None:
            return {"error": "dataset spec not found"}
        items = session.exec(select(DatasetItem).where(DatasetItem.dataset_version_id == version_id)).all()
        export_items = [
            ExportItem(
                id=item.id,
                audio=str(item.metadata_snapshot.get("stored_path", "")),
                text=item.text,
                duration=item.duration_sec,
                sample_type=item.sample_type,
                metadata=item.metadata_snapshot,
            )
            for item in sorted(items, key=lambda row: row.selection_rank)
        ]
        export_dir = config.app.data_dir / "exports" / spec.name / f"v{version.version:03d}"
        result = export_dataset(
            export_dir=export_dir,
            dataset_name=spec.name,
            version=version.version,
            target_keyword=spec.target_keyword,
            sampling_seed=version.sampling_seed,
            items=export_items,
            coverage_summary=version.coverage_summary,
        )
        version.export_path = str(result.export_dir.resolve())
        version.exported_at = datetime.now(timezone.utc)
        version.build_status = "exported"
        session.add(version)
        session.commit()
    return {
        "export_dir": str(result.export_dir),
        "manifest": str(result.manifest_path),
        "rich_manifest": str(result.rich_manifest_path),
        "dataset_yaml": str(result.dataset_yaml_path),
        "coverage_summary": str(result.coverage_summary_path),
        "eval_config_snippet": str(result.eval_config_snippet_path),
        "negative_hours": result.negative_hours,
    }
```

- [ ] **Step 6: Run all backend tests**

Run:

```bash
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 9**

```bash
git add kws_testset/services/export_service.py kws_testset/api/datasets.py tests/test_export_service.py
git commit -m "feat: add dataset export"
```

---

### Task 10: Taxonomy API and Minimal Static Web Shell

**Files:**
- Create: `/Users/e4/Documents/kws_testset/kws_testset/api/taxonomy.py`
- Create: `/Users/e4/Documents/kws_testset/kws_testset/web/index.html`
- Modify: `/Users/e4/Documents/kws_testset/kws_testset/app.py`
- Modify: `/Users/e4/Documents/kws_testset/tests/test_smoke.py`

- [ ] **Step 1: Write failing health and taxonomy route tests**

Add to `/Users/e4/Documents/kws_testset/tests/test_smoke.py`:

```python
def test_health_and_taxonomy_endpoints(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    taxonomy = client.get("/api/taxonomy").json()
    assert "wake_positive" in taxonomy["sample_type"]
    assert "device_denoise" in taxonomy["impairment_type"]


def test_web_shell_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "KWS Testset Platform" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_smoke.py::test_health_and_taxonomy_endpoints tests/test_smoke.py::test_web_shell_served -v
```

Expected: taxonomy and web shell assertions fail.

- [ ] **Step 3: Implement taxonomy API**

Create `/Users/e4/Documents/kws_testset/kws_testset/api/taxonomy.py`:

```python
from __future__ import annotations

from fastapi import APIRouter

from kws_testset.taxonomy import as_dict

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("")
def get_taxonomy() -> dict[str, list[str]]:
    return as_dict()
```

- [ ] **Step 4: Create minimal static web shell**

Create `/Users/e4/Documents/kws_testset/kws_testset/web/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>KWS Testset Platform</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.5; }
    code, pre { background: #f5f5f5; padding: 0.2rem 0.4rem; border-radius: 4px; }
    section { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
    button { padding: 0.4rem 0.8rem; }
    textarea { width: 100%; min-height: 8rem; }
  </style>
</head>
<body>
  <h1>KWS Testset Platform</h1>
  <p>本页面是第一版最小 Web 壳。核心能力通过 API 提供，交互可先使用 Swagger UI：<a href="/docs">/docs</a>。</p>

  <section>
    <h2>Health</h2>
    <button onclick="loadHealth()">检查服务</button>
    <pre id="health">未检查</pre>
  </section>

  <section>
    <h2>Taxonomy</h2>
    <button onclick="loadTaxonomy()">加载枚举</button>
    <pre id="taxonomy">未加载</pre>
  </section>

  <section>
    <h2>常用 API</h2>
    <ul>
      <li><code>POST /api/imports/scan</code> 扫描 wav</li>
      <li><code>POST /api/imports</code> 导入 source + original variant</li>
      <li><code>GET /api/assets</code> 查看资产</li>
      <li><code>POST /api/dataset-specs</code> 创建测试集规格</li>
      <li><code>POST /api/dataset-specs/{id}/build</code> 构建版本</li>
      <li><code>POST /api/dataset-versions/{id}/export</code> 导出 manifest</li>
    </ul>
  </section>

  <script>
    async function loadHealth() {
      const response = await fetch('/api/health');
      document.getElementById('health').textContent = JSON.stringify(await response.json(), null, 2);
    }
    async function loadTaxonomy() {
      const response = await fetch('/api/taxonomy');
      document.getElementById('taxonomy').textContent = JSON.stringify(await response.json(), null, 2);
    }
  </script>
</body>
</html>
```

- [ ] **Step 5: Serve static web shell**

Modify `/Users/e4/Documents/kws_testset/kws_testset/app.py`:

```python
from fastapi.responses import HTMLResponse
from kws_testset.api.taxonomy import router as taxonomy_router
```

inside `create_app` before routers are returned:

```python
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        web_path = Path(__file__).parent / "web" / "index.html"
        return web_path.read_text(encoding="utf-8")
```

inside `create_app` before `return app`:

```python
    app.include_router(taxonomy_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_smoke.py::test_health_and_taxonomy_endpoints tests/test_smoke.py::test_web_shell_served -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 10**

```bash
git add kws_testset/api/taxonomy.py kws_testset/web/index.html kws_testset/app.py tests/test_smoke.py
git commit -m "feat: add taxonomy api and web shell"
```

---

### Task 11: README, Cross-Platform Run Commands, and Final Minimum Test Pass

**Files:**
- Create or replace: `/Users/e4/Documents/kws_testset/README.md`

- [ ] **Step 1: Write README with exact run commands**

Create `/Users/e4/Documents/kws_testset/README.md`:

```markdown
# KWS Testset Platform

本项目是一个本地运行的关键词唤醒测试集创建与管理平台。第一版 MVP 支持：

- 扫描 WAV 文件并读取 duration/sample_rate/channels/hash。
- 人工提交 metadata 后导入为 `audio_source` + `audio_variant(original)`。
- 管理 ready 音频资产。
- 创建 dataset spec。
- 按 quota、include/exclude、固定 seed 构建 dataset version。
- 导出 `manifest.jsonl`、`rich_manifest.jsonl`、`dataset.yaml`、`coverage_summary.json`、`eval_config_snippet.yaml`。

## Requirements

- Python 3.11+
- uv

## Install

```bash
uv sync --extra dev
```

## Configure

默认配置文件：

```text
configs/app.yaml
```

默认数据目录：

```text
data/
```

Windows/Linux/macOS 都通过配置文件设置本机路径。代码使用 `pathlib.Path` 解析路径。

## Doctor

```bash
uv run kws-testset doctor
```

期望输出包含：

```text
doctor=ok
```

## Run Server

```bash
uv run kws-testset serve
```

打开：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## Test

```bash
uv run pytest -v
```

## Export to Existing sherpa_eval Project

在 `configs/app.yaml` 中配置本机评测项目路径：

```yaml
eval_project:
  root: /Users/e4/Library/Mobile Documents/com~apple~CloudDocs/自定义唤醒
  manifest_dir: sherpa_eval/data
```

第一版导出会生成 `eval_config_snippet.yaml`。将其中内容复制到评测项目的 experiment config 即可运行离线评测。
```

- [ ] **Step 2: Run full minimum test suite**

Run:

```bash
uv run pytest -v
```

Expected: PASS for all tests.

- [ ] **Step 3: Run doctor and start-server import check**

Run:

```bash
uv run kws-testset doctor
```

Expected output includes:

```text
doctor=ok
```

Run:

```bash
uv run python -c "from kws_testset.app import create_app; app = create_app(); print(app.title)"
```

Expected output:

```text
KWS Testset Platform
```

- [ ] **Step 4: Commit Task 11**

```bash
git add README.md
git commit -m "docs: add mvp run instructions"
```

---

## Final Verification Before Completion

- [ ] Run the full minimum test suite:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] Run doctor:

```bash
uv run kws-testset doctor
```

Expected output includes `doctor=ok`.

- [ ] Confirm server app imports:

```bash
uv run python -c "from kws_testset.app import create_app; app = create_app(); print(app.title)"
```

Expected output is `KWS Testset Platform`.

- [ ] Confirm repository status:

```bash
git status --short
```

Expected: no unexpected untracked or modified implementation files.

## Plan Self-Review

Spec coverage:

- Cross-platform config and paths: Task 1 and Task 11.
- Minimum tests: Tasks 1, 2, 3, 7, 9, and final verification.
- Audio source/variant schema: Task 4.
- WAV import and metadata commit: Tasks 5 and 6.
- Ready/semantic gate: Tasks 2 and 6.
- Dataset spec/version/item snapshot: Task 8.
- Rule sampling with include/exclude and seed: Task 7 and Task 8.
- Export manifest/rich manifest/dataset.yaml/eval snippet: Task 9.
- Local runnable platform: Tasks 1, 5, 10, and 11.

Known scope boundaries:

- This plan uses a minimal static web shell instead of a full React UI to satisfy the user's request to get the project running first.
- Rich browser-based metadata editing remains outside this MVP plan; the API and database boundaries are ready for it.
