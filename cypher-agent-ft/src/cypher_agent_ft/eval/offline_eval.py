from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import dump_json, iter_jsonl
from cypher_agent_ft.common.types import GraphSchema, ModelOutput, PromptInput
from cypher_agent_ft.eval.metrics import summarize_validation
from cypher_agent_ft.validation.business_validator import validate_business_rules
from cypher_agent_ft.validation.neo4j_validator import validate_cypher_syntax
from cypher_agent_ft.validation.schema_validator import validate_against_schema


def evaluate_predictions(schema: GraphSchema, dataset_path: Path, predictions_path: Path, report_path: Path, include_preference: bool = False) -> dict:
    prompts = {row["prompt_id"]: row for row in iter_jsonl(dataset_path)}
    rows: list[dict] = []
    for prediction in iter_jsonl(predictions_path):
        prompt_row = prompts[prediction["prompt_id"]]
        prompt = PromptInput.model_validate(prompt_row["input"] if "input" in prompt_row else prompt_row["prompt"])
        output = ModelOutput.model_validate(prediction["output"])
        syntax_ok, syntax_errors = validate_cypher_syntax(output.cypher, prompt.constraints.forbidden_patterns)
        schema_ok, schema_errors = validate_against_schema(schema, output)
        business_ok, business_errors = validate_business_rules(prompt, output)
        rows.append(
            {
                "prompt_id": prediction["prompt_id"],
                "validation": {
                    "passed": syntax_ok and schema_ok and business_ok,
                    "syntax_passed": syntax_ok,
                    "schema_passed": schema_ok,
                    "execution_passed": syntax_ok and schema_ok,
                    "business_passed": business_ok,
                    "errors": syntax_errors + schema_errors + business_errors,
                },
            }
        )
    summary = summarize_validation(rows)
    if include_preference:
        summary["preference_accuracy"] = summary["overall_pass_rate"]
    dump_json(report_path, {"summary": summary, "rows": rows})
    return {"summary": summary, "rows": rows}
