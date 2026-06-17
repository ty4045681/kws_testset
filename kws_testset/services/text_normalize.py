from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str, *, upper: bool = True, space_to_underscore: bool = True) -> str:
    value = unicodedata.normalize("NFKC", text or "").strip()
    value = re.sub(r"\s+", " ", value)
    if upper:
        value = value.upper()
    if space_to_underscore:
        value = value.replace(" ", "_")
    return value


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)
    return normalized_keyword != "" and normalized_keyword in normalized_text
