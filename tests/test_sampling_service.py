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

    result = sample_candidates(candidates, {"wake_positive": 2}, ["gender", "noise_scene"], 123, overrides)
    result_again = sample_candidates(candidates, {"wake_positive": 2}, ["gender", "noise_scene"], 123, overrides)

    assert [item.variant_id for item in result.items] == [item.variant_id for item in result_again.items]
    assert "var_1" not in [item.variant_id for item in result.items]
    assert "var_4" in [item.variant_id for item in result.items]
    assert result.counts_by_sample_type["wake_positive"] == 2
    assert result.shortfalls == {}


def test_sampling_reports_shortfall_without_backfilling_other_types():
    candidates = [candidate(1, "similar_negative")]

    result = sample_candidates(candidates, {"similar_negative": 3, "wake_positive": 2}, ["gender"], 123, [])

    assert result.counts_by_sample_type["similar_negative"] == 1
    assert result.shortfalls == {"similar_negative": 2, "wake_positive": 2}
