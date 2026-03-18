from __future__ import annotations

from _bootstrap import ROOT
from cypher_agent_ft.common.io import iter_jsonl, write_jsonl
from cypher_agent_ft.common.types import CandidateRecord, PromptInput, ValidationResult
from cypher_agent_ft.schema.loader import load_schema
from cypher_agent_ft.teacher.parser import parse_model_output
from cypher_agent_ft.validation.business_validator import validate_business_rules
from cypher_agent_ft.validation.neo4j_validator import validate_cypher_syntax
from cypher_agent_ft.validation.schema_validator import validate_against_schema


def main() -> None:
    schema = load_schema(ROOT / "configs" / "schema.yaml")
    rows = []
    for row in iter_jsonl(ROOT / "data" / "intermediate" / "candidate_pool.jsonl"):
        prompt = PromptInput.model_validate(row["input"])
        output = parse_model_output(row["output"])
        syntax_ok, syntax_errors = validate_cypher_syntax(output.cypher, prompt.constraints.forbidden_patterns)
        schema_ok, schema_errors = validate_against_schema(schema, output)
        business_ok, business_errors = validate_business_rules(prompt, output)
        validation = ValidationResult(
            passed=syntax_ok and schema_ok and business_ok,
            syntax_passed=syntax_ok,
            schema_passed=schema_ok,
            business_passed=business_ok,
            execution_passed=syntax_ok and schema_ok,
            errors=syntax_errors + schema_errors + business_errors,
            score=(0.35 if syntax_ok else 0.0) + (0.3 if schema_ok else 0.0) + (0.35 if business_ok else 0.0),
        )
        record = CandidateRecord(
            candidate_id=row["candidate_id"],
            prompt_id=row["prompt_id"],
            source=row["source"],
            input=prompt,
            output=output,
            validation=validation,
        )
        rows.append(record.model_dump(mode="json"))
    write_jsonl(ROOT / "data" / "processed" / "validated_candidates.jsonl", rows)
    print(f"validated {len(rows)} candidates")


if __name__ == "__main__":
    main()
