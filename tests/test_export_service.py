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


def test_export_dataset_preserves_small_nonzero_negative_hours(tmp_path: Path):
    items = [
        ExportItem(
            id="utt_small_neg",
            audio="/abs/small_neg.wav",
            text="你好小志",
            duration=1.5,
            sample_type="ordinary_negative",
            metadata={"sample_type": "ordinary_negative"},
        )
    ]

    result = export_dataset(
        export_dir=tmp_path / "exports" / "small_negative" / "v001",
        dataset_name="small_negative",
        version=1,
        target_keyword="你好小智",
        sampling_seed=7,
        items=items,
        coverage_summary={"total": 1},
    )

    assert result.negative_hours == 0.000417
    assert "negative_hours: 0.000417" in (result.export_dir / "dataset.yaml").read_text(encoding="utf-8")
