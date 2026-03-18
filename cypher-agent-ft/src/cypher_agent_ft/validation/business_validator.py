from __future__ import annotations

import re

from cypher_agent_ft.common.types import PromptInput, ModelOutput
from cypher_agent_ft.common.utils import choose_primary_component, choose_primary_signal


def validate_business_rules(prompt: PromptInput, output: ModelOutput) -> tuple[bool, list[str]]:
    errors: list[str] = []
    cypher = output.cypher
    if prompt.constraints.must_filter_component:
        component = choose_primary_component(prompt.parsed_question.entities)
        if component and component not in cypher:
            errors.append("missing component filter")
    signal = choose_primary_signal(prompt.parsed_question.entities)
    if prompt.parsed_question.question_type in {"cause_trace", "action_lookup", "multi_hop_root_cause", "validation_check"}:
        if signal and signal not in cypher:
            errors.append("missing signal filter")
    for field in prompt.constraints.must_return:
        if field not in cypher:
            errors.append(f"missing return field: {field}")
    for relation in output.query_plan.required_relations:
        if relation not in cypher:
            errors.append(f"missing required relation: {relation}")
    match = re.search(r"\*1\.\.(\d+)", cypher)
    if match and int(match.group(1)) > prompt.constraints.max_hops:
        errors.append("hop constraint violated")
    return not errors, errors
