from __future__ import annotations

import re
from pathlib import Path

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def safe_slug(value: str, fallback: str = "dataset") -> str:
    slug = _SAFE_CHARS.sub("_", value.strip())
    slug = slug.strip("._-")
    return slug or fallback


def safe_child_dir(root: Path, child_name: str) -> Path:
    root_resolved = root.resolve()
    child = (root_resolved / safe_slug(child_name)).resolve()
    if child != root_resolved and root_resolved not in child.parents:
        raise ValueError(f"unsafe child path: {child_name}")
    return child
