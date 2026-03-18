from __future__ import annotations

import re

from app.domain.enums import RiskLevel
from app.risk.risk_rules import list_rules


def classify_risk(question: str, entities: list[str]) -> RiskLevel:
    score = 0
    for rule in list_rules():
        if not rule.get("enabled"):
            continue
        if re.search(rule["content"], question):
            score += 2 if rule["level"] == "high" else 1
    if len(entities) >= 3:
        score += 1
    if score >= 3:
        return RiskLevel.HIGH
    if score >= 1:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
