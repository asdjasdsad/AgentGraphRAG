from __future__ import annotations

from app.core.db_mysql import risk_rules_table


DEFAULT_RULES = [
    {"rule_id": "risk_001", "rule_type": "keyword", "content": "失效|停飞|安全事故", "level": "high", "enabled": True},
    {"rule_id": "risk_002", "rule_type": "keyword", "content": "整改|根因", "level": "medium", "enabled": True},
]


def bootstrap_risk_rules() -> None:
    if risk_rules_table.all():
        return
    for rule in DEFAULT_RULES:
        risk_rules_table.upsert(rule, "rule_id")


def list_rules() -> list[dict]:
    bootstrap_risk_rules()
    return risk_rules_table.all()


def allowed_scope_for_user(user_id: str) -> list[str]:
    return ["documents", "chunks", "graph", "cases"] if user_id else ["chunks"]
