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
