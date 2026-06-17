from __future__ import annotations

from fastapi import APIRouter

from kws_testset.taxonomy import as_dict

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("")
def get_taxonomy() -> dict[str, list[str]]:
    return as_dict()
