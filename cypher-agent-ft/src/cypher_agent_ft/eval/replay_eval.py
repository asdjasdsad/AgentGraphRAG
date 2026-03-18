from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import dump_json, iter_jsonl
from cypher_agent_ft.common.types import GraphSchema, ModelOutput, PromptInput
from cypher_agent_ft.eval.metrics import ratio
from cypher_agent_ft.validation.business_validator import validate_business_rules
from cypher_agent_ft.validation.neo4j_validator import validate_cypher_syntax
from cypher_agent_ft.validation.schema_validator import validate_against_schema


def evaluate_replay(schema: GraphSchema, replay_path: Path, baseline_predictions: Path, tuned_predictions: Path, report_path: Path) -> dict:
    replay_prompts = {row["prompt_id"]: row for row in iter_jsonl(replay_path)}

    def score(path: Path) -> dict:
        rows = []
        for prediction in iter_jsonl(path):
            prompt_row = replay_prompts[prediction["prompt_id"]]
            prompt = PromptInput.model_validate(prompt_row["input"] if "input" in prompt_row else prompt_row["prompt"])
            output = ModelOutput.model_validate(prediction["output"])
            syntax_ok, _ = validate_cypher_syntax(output.cypher, prompt.constraints.forbidden_patterns)
            schema_ok, _ = validate_against_schema(schema, output)
            business_ok, _ = validate_business_rules(prompt, output)
            rows.append({"hit": syntax_ok and schema_ok and business_ok, "fallback": not (syntax_ok and schema_ok and business_ok), "constraint_violation": not business_ok})
        total = len(rows)
        return {
            "rows": rows,
            "summary": {
                "graph_retrieval_hit_rate": ratio(sum(1 for row in rows if row["hit"]), total),
                "fallback_trigger_rate": ratio(sum(1 for row in rows if row["fallback"]), total),
                "constraint_violation_rate": ratio(sum(1 for row in rows if row["constraint_violation"]), total),
            },
        }

    baseline = score(baseline_predictions)
    tuned = score(tuned_predictions)
    report = {"baseline": baseline["summary"], "tuned": tuned["summary"], "delta": {key: round(tuned["summary"][key] - baseline["summary"][key], 4) for key in tuned["summary"]}}
    dump_json(report_path, report)
    return report
