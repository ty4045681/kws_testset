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
