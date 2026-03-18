from __future__ import annotations


def ratio(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) if denominator else 0.0, 4)


def summarize_validation(rows: list[dict]) -> dict[str, float | int]:
    total = len(rows)
    syntax = sum(1 for row in rows if row["validation"]["syntax_passed"])
    schema = sum(1 for row in rows if row["validation"]["schema_passed"])
    execution = sum(1 for row in rows if row["validation"]["execution_passed"])
    business = sum(1 for row in rows if row["validation"]["business_passed"])
    passed = sum(1 for row in rows if row["validation"]["passed"])
    return {
        "total": total,
        "syntax_pass_rate": ratio(syntax, total),
        "schema_compliance": ratio(schema, total),
        "execution_success_rate": ratio(execution, total),
        "business_logic_accuracy": ratio(business, total),
        "overall_pass_rate": ratio(passed, total),
    }
