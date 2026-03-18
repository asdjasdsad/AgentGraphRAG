from __future__ import annotations

import hashlib
import re
from copy import deepcopy

from cypher_agent_ft.common.types import ModelOutput, PromptInput, QueryPlan


def stable_id(prefix: str, seed: str) -> str:
    return f"{prefix}_{hashlib.md5(seed.encode('utf-8')).hexdigest()[:12]}"


def deterministic_split(seed: str) -> str:
    value = int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
    if value < 70:
        return "train"
    if value < 85:
        return "val"
    return "test"


def choose_primary_component(entities: list[str]) -> str | None:
    for item in entities:
        if item.endswith("泵") or item.endswith("筒") or item.endswith("阀"):
            return item
    return entities[0] if entities else None


def choose_primary_signal(entities: list[str]) -> str | None:
    if len(entities) >= 2:
        return entities[1]
    return entities[0] if entities else None


def build_reference_output(prompt: PromptInput) -> ModelOutput:
    question = prompt.parsed_question
    component = choose_primary_component(question.entities) or "液压泵"
    signal = choose_primary_signal(question.entities) or "异常"
    max_hops = prompt.constraints.max_hops
    if question.question_type == "cause_trace":
        return ModelOutput(
            query_plan=QueryPlan(
                target_nodes=["Cause"],
                required_relations=["INVOLVES_COMPONENT", "CAUSES"],
                filters=[f"Component.canonical_name = {component}", f"Phenomenon.canonical_name CONTAINS {signal}"],
                max_hops=max_hops,
            ),
            cypher=(
                "MATCH (i:Issue)-[:INVOLVES_COMPONENT]->(c:Component) "
                "MATCH (cause:Cause)-[:CAUSES]->(p:Phenomenon) "
                f"WHERE c.canonical_name = '{component}' AND p.canonical_name CONTAINS '{signal}' "
                "OPTIONAL MATCH (doc:Document)-[:CONTAINS]->(:Chunk)-[:MENTIONS]->(cause) "
                "RETURN cause.canonical_name AS cause_name, collect(DISTINCT doc.document_id) AS source_doc_ids"
            ),
        )
    if question.question_type == "action_lookup":
        return ModelOutput(
            query_plan=QueryPlan(
                target_nodes=["Action"],
                required_relations=["CAUSES", "MITIGATES"],
                filters=[f"Phenomenon.canonical_name CONTAINS {signal}"],
                max_hops=max_hops,
            ),
            cypher=(
                "MATCH (cause:Cause)-[:CAUSES]->(p:Phenomenon) "
                "MATCH (action:Action)-[:MITIGATES]->(cause) "
                f"WHERE p.canonical_name CONTAINS '{signal}' "
                "RETURN DISTINCT action.canonical_name AS action_name, cause.canonical_name AS cause_name"
            ),
        )
    if question.question_type == "source_trace":
        return ModelOutput(
            query_plan=QueryPlan(
                target_nodes=["Document", "Chunk"],
                required_relations=["CONTAINS", "MENTIONS"],
                filters=[f"Cause.canonical_name CONTAINS {signal}"],
                max_hops=max_hops,
            ),
            cypher=(
                "MATCH (doc:Document)-[:CONTAINS]->(chunk:Chunk)-[:MENTIONS]->(cause:Cause) "
                f"WHERE cause.canonical_name CONTAINS '{signal}' "
                "RETURN doc.document_id AS source_doc_id, chunk.chunk_id AS chunk_id, chunk.page_no AS page_no"
            ),
        )
    if question.question_type == "multi_hop_root_cause":
        return ModelOutput(
            query_plan=QueryPlan(
                target_nodes=["Cause"],
                required_relations=["CAUSES"],
                filters=[f"Phenomenon.canonical_name CONTAINS {signal}"],
                max_hops=max_hops,
            ),
            cypher=(
                "MATCH path = (root:Cause)-[:CAUSES*1..2]->(p:Phenomenon) "
                f"WHERE p.canonical_name CONTAINS '{signal}' "
                "RETURN [node IN nodes(path) | coalesce(node.canonical_name, node.issue_id)] AS cause_chain, length(path) AS hop_count"
            ),
        )
    return ModelOutput(
        query_plan=QueryPlan(
            target_nodes=["Issue", "Action"],
            required_relations=["INVOLVES_COMPONENT", "CAUSES", "MITIGATES"],
            filters=[f"Component.canonical_name = {component}", f"Phenomenon.canonical_name CONTAINS {signal}"],
            max_hops=max_hops,
        ),
        cypher=(
            "MATCH (i:Issue)-[:INVOLVES_COMPONENT]->(c:Component) "
            "MATCH (cause:Cause)-[:CAUSES]->(p:Phenomenon) "
            "OPTIONAL MATCH (action:Action)-[:MITIGATES]->(cause) "
            f"WHERE c.canonical_name = '{component}' AND p.canonical_name CONTAINS '{signal}' "
            "RETURN i.issue_id AS issue_id, cause.canonical_name AS cause_name, collect(DISTINCT action.canonical_name) AS action_names"
        ),
    )


def perturb_output(output: ModelOutput, mode: str) -> ModelOutput:
    bad = deepcopy(output)
    if mode == "missing_filter":
        bad.query_plan.filters = bad.query_plan.filters[:1]
        bad.cypher = re.sub(r" AND [^R]+(?= RETURN| OPTIONAL MATCH)", "", bad.cypher, count=1)
    elif mode == "reverse_relation":
        bad.query_plan.required_relations = list(dict.fromkeys(bad.query_plan.required_relations))
        bad.cypher = bad.cypher.replace("<-[:CAUSES]-", "-[:CAUSES]->").replace("-[:MITIGATES]->", "<-[:MITIGATES]-")
    elif mode == "bad_return":
        bad.cypher = re.sub(r"RETURN .+$", "RETURN cause.name AS cause", bad.cypher)
    elif mode == "over_broad":
        bad.cypher = re.sub(r"WHERE .+? RETURN", "RETURN", bad.cypher)
    elif mode == "hop_error":
        bad.query_plan.max_hops += 2
        bad.cypher = bad.cypher.replace("*1..2", "*1..5")
    return bad
