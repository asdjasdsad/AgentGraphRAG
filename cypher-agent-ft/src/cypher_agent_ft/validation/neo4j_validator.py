from __future__ import annotations

import re


def validate_cypher_syntax(cypher: str, forbidden_patterns: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    upper = cypher.upper()
    if "MATCH" not in upper or "RETURN" not in upper:
        errors.append("cypher must include MATCH and RETURN")
    if cypher.count("(") != cypher.count(")") or cypher.count("[") != cypher.count("]"):
        errors.append("unbalanced brackets")
    if re.search(r"\bMATCH\s*\(\w*\)\s*RETURN\b", upper):
        errors.append("full graph scan detected")
    for pattern in forbidden_patterns:
        if pattern == "unbounded_match" and re.search(r"\*\s*\]", cypher):
            errors.append("unbounded path match")
        if pattern == "full_graph_scan" and re.search(r"MATCH\s*\([^)]*\)\s*RETURN", upper):
            errors.append("full graph scan")
    return not errors, errors
