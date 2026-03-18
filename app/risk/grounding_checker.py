from __future__ import annotations


def is_grounded(answer: str, evidence: list[dict]) -> bool:
    if not answer:
        return False
    if not evidence:
        return False
    return any(item.get("content") and item["content"][:4] in answer for item in evidence if item.get("content"))
