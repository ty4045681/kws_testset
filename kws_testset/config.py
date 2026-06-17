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
