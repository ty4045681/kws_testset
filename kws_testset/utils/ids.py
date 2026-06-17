from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def short_hash(value: str, length: int = 12) -> str:
    return value[:length]


def dated_id(prefix: str, hash_value: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{stamp}_{short_hash(hash_value)}"


def new_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{stamp}_{uuid4().hex[:12]}"
