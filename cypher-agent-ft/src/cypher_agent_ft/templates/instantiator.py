from __future__ import annotations

from cypher_agent_ft.common.types import ParsedQuestion, PromptInput, QueryConstraints, TaskTemplate
from cypher_agent_ft.schema.cutter import cut_schema_for_task


def instantiate_prompt(template: TaskTemplate, schema, rules: dict, entity_sample: dict[str, str]) -> PromptInput:
    component = entity_sample["component"]
    phenomenon = entity_sample["phenomenon"]
    cause = entity_sample["cause"]
    action = entity_sample["action"]
    anchor = {"cause_trace": cause, "source_trace": cause, "action_lookup": action}.get(template.question_type, phenomenon)
    user_query = template.nl_template.format(component=component, phenomenon=phenomenon, cause=cause, action=action)
    constraints = QueryConstraints(
        max_hops=template.max_hops,
        must_filter_component=template.must_include_component,
        must_return=template.must_return or rules["business_rules"]["must_return_defaults"].get(template.question_type, []),
        forbidden_patterns=rules["business_rules"]["forbidden_patterns"],
    )
    parsed_question = ParsedQuestion(
        question_type=template.question_type,
        entities=[component, phenomenon, anchor],
        relation_type=template.relation_type,
        constraints=[f"task_type:{template.task_type}"],
        need_multihop=template.need_multihop,
    )
    return PromptInput(
        user_query=user_query,
        parsed_question=parsed_question,
        schema_context=cut_schema_for_task(schema, template),
        constraints=constraints,
    )
