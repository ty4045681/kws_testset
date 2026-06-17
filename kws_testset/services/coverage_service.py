from __future__ import annotations

from collections import Counter
from typing import Any


def count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter = Counter(str(item.get(field, "unknown")) for item in items)
    return dict(sorted(counter.items()))


def build_coverage_summary(items: list[dict[str, Any]], fields: list[str], shortfalls: dict[str, int]) -> dict[str, Any]:
    unique_fields = list(dict.fromkeys(fields))
    return {
        "total": len(items),
        "shortfalls": shortfalls,
        "by_field": {field: count_by_field(items, field) for field in unique_fields},
    }
