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
