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
