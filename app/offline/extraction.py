from __future__ import annotations

import re

from app.domain.ontology import RELATION_TYPES
from app.domain.schemas import Entity, ExtractionResult, Relation
from app.prompts import render_prompt
from app.utils.alias_map import normalize_alias


COMPONENT_HINTS = ["液压泵", "密封圈", "阀门", "轴承", "传感器", "作动筒", "管路"]
PHENOMENON_HINTS = ["泄漏", "渗漏", "异响", "裂纹", "过热", "失效", "松动", "卡滞"]
CAUSE_HINTS = ["老化", "磨损", "腐蚀", "装配不良", "疲劳", "污染", "密封失效"]
ACTION_HINTS = ["更换", "维修", "整改", "校准", "复测", "清洗", "加固"]


def _extract_by_hints(text: str, hints: list[str], entity_type: str) -> list[Entity]:
    entities: list[Entity] = []
    for hint in hints:
        if hint in text:
            entities.append(Entity(name=normalize_alias(hint), type=entity_type))
    return entities


def extract_entities_relations(text: str, doc_type: str) -> dict:
    prompt_blueprint = render_prompt("extract_entities", doc_type=doc_type, text=text)
    entities = []
    entities.extend(_extract_by_hints(text, COMPONENT_HINTS, "Component"))
    entities.extend(_extract_by_hints(text, PHENOMENON_HINTS, "Phenomenon"))
    entities.extend(_extract_by_hints(text, CAUSE_HINTS, "Cause"))
    entities.extend(_extract_by_hints(text, ACTION_HINTS, "Action"))
    matched_issue = re.search(r"Q\d{4}-\d{3,}", text)
    if matched_issue:
        entities.append(Entity(name=matched_issue.group(0), type="Issue"))
    deduped = {(entity.name, entity.type): entity for entity in entities}
    entities = list(deduped.values())
    relations: list[Relation] = []
    causes = [entity.name for entity in entities if entity.type == "Cause"]
    phenomena = [entity.name for entity in entities if entity.type == "Phenomenon"]
    actions = [entity.name for entity in entities if entity.type == "Action"]
    components = [entity.name for entity in entities if entity.type == "Component"]
    issues = [entity.name for entity in entities if entity.type == "Issue"]
    for cause in causes:
        for phenomenon in phenomena:
            relations.append(Relation(source=cause, type=RELATION_TYPES["causes"], target=phenomenon))
    for action in actions:
        for cause in causes:
            relations.append(Relation(source=action, type=RELATION_TYPES["mitigates"], target=cause))
    for issue in issues:
        for phenomenon in phenomena:
            relations.append(Relation(source=issue, type=RELATION_TYPES["has_phenomenon"], target=phenomenon))
        for component in components:
            relations.append(Relation(source=issue, type=RELATION_TYPES["involves_component"], target=component))
        for action in actions:
            relations.append(Relation(source=issue, type=RELATION_TYPES["has_action"], target=action))
    result = ExtractionResult(entities=entities, relations=relations).model_dump(mode="json")
    result["prompt_blueprint_length"] = len(prompt_blueprint)
    return result
