from __future__ import annotations

import argparse

from _bootstrap import ROOT
from cypher_agent_ft.common.io import write_jsonl
from cypher_agent_ft.common.utils import stable_id
from cypher_agent_ft.schema.loader import load_schema
from cypher_agent_ft.templates.instantiator import instantiate_prompt
from cypher_agent_ft.templates.task_sampler import load_rules, load_task_templates, sample_entities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    schema = load_schema(ROOT / "configs" / "schema.yaml")
    rules = load_rules(ROOT / "configs" / "rules.yaml")
    templates = load_task_templates(ROOT / "configs" / "task_templates.yaml")
    rows = []
    per_template = max(1, args.limit // max(1, len(templates)))
    for template in templates:
        for sample in sample_entities(rules, template.task_type, per_template):
            prompt = instantiate_prompt(template, schema, rules, sample)
            prompt_id = stable_id("prompt", f"{template.task_type}:{prompt.user_query}")
            rows.append({"prompt_id": prompt_id, "template": template.task_type, "input": prompt.model_dump(mode="json")})
    write_jsonl(ROOT / "data" / "intermediate" / "prompt_pool.jsonl", rows)
    print(f"built {len(rows)} prompts")


if __name__ == "__main__":
    main()
