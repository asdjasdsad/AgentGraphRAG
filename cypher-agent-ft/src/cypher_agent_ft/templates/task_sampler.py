from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import load_config
from cypher_agent_ft.common.types import TaskTemplate


def load_task_templates(path: Path) -> list[TaskTemplate]:
    return [TaskTemplate.model_validate(item) for item in load_config(path)]


def load_rules(path: Path) -> dict:
    return load_config(path)


def sample_entities(rules: dict, task_type: str, limit: int) -> list[dict[str, str]]:
    catalog = rules["entity_catalog"]
    components = catalog["components"]
    phenomena = catalog["phenomena"]
    causes = catalog["causes"]
    actions = catalog["actions"]
    documents = catalog["documents"]
    pairs: list[dict[str, str]] = []
    for index in range(limit):
        pairs.append(
            {
                "component": components[index % len(components)],
                "phenomenon": phenomena[index % len(phenomena)],
                "cause": causes[index % len(causes)],
                "action": actions[index % len(actions)],
                "document": documents[index % len(documents)],
                "task_type": task_type,
            }
        )
    return pairs
