from kws_testset.services.text_normalize import contains_keyword, normalize_text


def test_normalize_chinese_keeps_text_and_trims_spaces():
    assert normalize_text("  你好小智  ") == "你好小智"


def test_normalize_english_uppercases_and_uses_underscore():
    assert normalize_text(" hello   xiao zhi ") == "HELLO_XIAO_ZHI"


def test_contains_keyword_uses_normalized_forms():
    assert contains_keyword(" hello   xiao zhi ", "HELLO XIAO ZHI") is True
