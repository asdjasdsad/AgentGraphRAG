from __future__ import annotations

from collections.abc import Mapping


def merge_metadata(*items: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for item in items:
        merged.update(item)
    return merged
