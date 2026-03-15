from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from app.core.config import Settings, get_settings
from app.domain.schemas import Entity, Evidence, Relation


VALID_CYPHER_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def reset_neo4j_drivers() -> None:
    get_neo4j_driver.cache_clear()


@lru_cache(maxsize=4)
def get_neo4j_driver(uri: str, user: str, password: str):
    return GraphDatabase.driver(uri, auth=(user, password))


def _is_test_mode(settings: Settings) -> bool:
    return settings.app_env == "test"


def _validate_cypher_name(value: str, kind: str) -> str:
    if not VALID_CYPHER_NAME.match(value):
        raise ValueError(f"Unsafe {kind}: {value}")
    return value


def _sanitize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in properties.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
            sanitized[key] = value
        else:
            sanitized[key] = json.dumps(value, ensure_ascii=False)
    return sanitized


def _render_path(path: Any) -> tuple[str, dict[str, Any]]:
    nodes = list(path.nodes)
    relationships = list(path.relationships)
    segments: list[str] = []
    metadata = {"nodes": [], "relationships": []}
    for index, node in enumerate(nodes):
        node_data = dict(node)
        node_data["labels"] = list(node.labels)
        metadata["nodes"].append(node_data)
        segments.append(node_data.get("name", str(node.id)))
        if index < len(relationships):
            relation = relationships[index]
            relation_data = dict(relation)
            relation_data["type"] = relation.type
            relation_data["start_node"] = relation.start_node.get("name")
            relation_data["end_node"] = relation.end_node.get("name")
            metadata["relationships"].append(relation_data)
            segments.append(f"-[{relation.type}]->")
    return " ".join(segments), metadata


class GraphStore:
    def __init__(self) -> None:
        self.path = Path(get_settings().store_dir) / "graph.json"
        if not self.path.exists():
            self.path.write_text(json.dumps({"entities": [], "relations": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _settings(self) -> Settings:
        return get_settings()

    def _driver(self):
        settings = self._settings()
        return get_neo4j_driver(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _mock_upsert_graph(self, entities: list[Entity], relations: list[Relation]) -> None:
        data = self._read()
        entity_map = {(item["name"], item["type"]): item for item in data["entities"]}
        for entity in entities:
            entity_map[(entity.name, entity.type)] = entity.model_dump(mode="json")
        relation_map = {(item["source"], item["type"], item["target"]): item for item in data["relations"]}
        for relation in relations:
            relation_map[(relation.source, relation.type, relation.target)] = relation.model_dump(mode="json")
        data["entities"] = list(entity_map.values())
        data["relations"] = list(relation_map.values())
        self._write(data)

    def _mock_query(self, entity_names: list[str], relation_type: str | None = None, max_hops: int = 2) -> list[Evidence]:
        data = self._read()
        hits: list[Evidence] = []
        for relation in data["relations"]:
            if relation_type and relation["type"] != relation_type:
                continue
            if entity_names and relation["source"] not in entity_names and relation["target"] not in entity_names:
                continue
            content = f"{relation['source']} -[{relation['type']}]-> {relation['target']}"
            hits.append(Evidence(evidence_id=f"graph_{relation['source']}_{relation['target']}", source="neo4j", content=content, score=1.0 / max(1, max_hops), metadata=relation))
        return hits

    def upsert_graph(self, entities: list[Entity], relations: list[Relation]) -> None:
        settings = self._settings()
        if _is_test_mode(settings):
            self._mock_upsert_graph(entities, relations)
            return
        driver = self._driver()
        entity_types = {entity.name: entity.type for entity in entities}
        with driver.session(database=settings.neo4j_database) as session:
            for entity in entities:
                label = _validate_cypher_name(entity.type, "label")
                properties = _sanitize_properties(entity.attributes)
                properties["name"] = entity.name
                session.run(f"MERGE (n:{label} {{name: $name}}) SET n += $props", name=entity.name, props=properties)
            for relation in relations:
                relation_name = _validate_cypher_name(relation.type, "relationship type")
                source_label = _validate_cypher_name(entity_types.get(relation.source, "Entity"), "label")
                target_label = _validate_cypher_name(entity_types.get(relation.target, "Entity"), "label")
                session.run((f"MATCH (a:{source_label} {{name: $source_name}}), (b:{target_label} {{name: $target_name}}) " f"MERGE (a)-[r:{relation_name}]->(b) SET r += $props"), source_name=relation.source, target_name=relation.target, props=_sanitize_properties(relation.attributes))

    def query(self, entity_names: list[str], relation_type: str | None = None, max_hops: int = 2) -> list[Evidence]:
        settings = self._settings()
        if _is_test_mode(settings):
            return self._mock_query(entity_names, relation_type=relation_type, max_hops=max_hops)
        relation_pattern = f":{_validate_cypher_name(relation_type, 'relationship type')}" if relation_type else ""
        query = f"MATCH path = (a)-[{relation_pattern}*1..{max_hops}]-(b) WHERE size($entity_names) = 0 OR a.name IN $entity_names OR b.name IN $entity_names RETURN path LIMIT $limit"
        hits: list[Evidence] = []
        with self._driver().session(database=settings.neo4j_database) as session:
            result = session.run(query, entity_names=entity_names, limit=20)
            for index, record in enumerate(result):
                content, metadata = _render_path(record["path"])
                hop_count = max(1, len(metadata["relationships"]))
                hits.append(Evidence(evidence_id=f"graph_path_{index}", source="neo4j", content=content, score=1.0 / hop_count, metadata=metadata))
        return hits

    def snapshot(self, limit: int = 200) -> dict[str, Any]:
        settings = self._settings()
        if _is_test_mode(settings):
            data = self._read()
            return {"entities": data["entities"][:limit], "relations": data["relations"][:limit], "counts": {"entities": len(data["entities"]), "relations": len(data["relations"])}}
        try:
            entities: list[dict[str, Any]] = []
            relations: list[dict[str, Any]] = []
            with self._driver().session(database=settings.neo4j_database) as session:
                entity_result = session.run("MATCH (n) RETURN n.name AS name, labels(n) AS labels LIMIT $limit", limit=limit)
                for row in entity_result:
                    labels = row.get("labels") or []
                    entities.append({"name": row.get("name", ""), "type": labels[0] if labels else "Entity"})
                relation_result = session.run("MATCH (a)-[r]->(b) RETURN a.name AS source, type(r) AS type, b.name AS target LIMIT $limit", limit=limit)
                for row in relation_result:
                    relations.append({"source": row.get("source", ""), "type": row.get("type", ""), "target": row.get("target", "")})
            return {"entities": entities, "relations": relations, "counts": {"entities": len(entities), "relations": len(relations)}}
        except Exception as exc:
            return {"entities": [], "relations": [], "counts": {"entities": 0, "relations": 0}, "error": str(exc)}

    def ping(self) -> dict[str, Any]:
        settings = self._settings()
        if _is_test_mode(settings):
            return {"ok": True, "backend": "mock-neo4j"}
        try:
            driver = self._driver()
            driver.verify_connectivity()
            return {"ok": True, "backend": settings.neo4j_uri, "database": settings.neo4j_database}
        except Exception as exc:
            return {"ok": False, "backend": settings.neo4j_uri, "database": settings.neo4j_database, "error": str(exc)}


graph_store = GraphStore()
