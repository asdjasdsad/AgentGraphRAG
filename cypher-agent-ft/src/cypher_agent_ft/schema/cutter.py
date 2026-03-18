from __future__ import annotations

from cypher_agent_ft.common.types import GraphSchema, SchemaContext, TaskTemplate


def cut_schema_for_task(schema: GraphSchema, template: TaskTemplate) -> SchemaContext:
    relations = [item.pattern for item in schema.relation_types if item.type in set(template.required_relations)]
    node_types: dict[str, list[str]] = {}
    for relation in schema.relation_types:
        if relation.type not in set(template.required_relations):
            continue
        node_types[relation.source] = schema.node_types.get(relation.source, [])
        node_types[relation.target] = schema.node_types.get(relation.target, [])
    if not node_types:
        node_types = dict(schema.node_types)
        relations = [item.pattern for item in schema.relation_types]
    return SchemaContext(node_types=node_types, relation_types=relations)
