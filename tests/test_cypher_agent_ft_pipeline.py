from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT / "cypher-agent-ft"
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cypher_agent_ft.common.types import PromptInput
from cypher_agent_ft.common.utils import build_reference_output, perturb_output
from cypher_agent_ft.schema.loader import load_schema
from cypher_agent_ft.validation.business_validator import validate_business_rules
from cypher_agent_ft.validation.schema_validator import validate_against_schema


def test_bad_candidate_is_rejected() -> None:
    replay_row = json.loads((PROJECT_ROOT / "data" / "raw" / "replay_queries.jsonl").read_text(encoding="utf-8").splitlines()[0])
    prompt = PromptInput.model_validate(replay_row["input"])
    schema = load_schema(PROJECT_ROOT / "configs" / "schema.yaml")
    gold = build_reference_output(prompt)
    bad = perturb_output(gold, "missing_filter")
    schema_ok, _ = validate_against_schema(schema, gold)
    business_ok, _ = validate_business_rules(prompt, gold)
    bad_business_ok, bad_errors = validate_business_rules(prompt, bad)
    assert schema_ok is True
    assert business_ok is True
    assert bad_business_ok is False
    assert any("missing" in error for error in bad_errors)


def test_cypher_agent_ft_end_to_end() -> None:
    commands = [
        ["python", "cypher-agent-ft/scripts/export_schema.py"],
        ["python", "cypher-agent-ft/scripts/build_prompt_pool.py", "--limit", "15"],
        ["python", "cypher-agent-ft/scripts/generate_candidates_gpt4o.py", "--mode", "mock"],
        ["python", "cypher-agent-ft/scripts/validate_candidates.py"],
        ["python", "cypher-agent-ft/scripts/build_sft_dataset.py"],
        ["python", "cypher-agent-ft/scripts/generate_sft_outputs.py", "--mode", "sft_mock", "--split", "test"],
        ["python", "cypher-agent-ft/scripts/build_dpo_dataset.py"],
        ["python", "cypher-agent-ft/scripts/eval_offline.py", "--stage", "sft"],
        ["python", "cypher-agent-ft/scripts/eval_offline.py", "--stage", "dpo"],
        ["python", "cypher-agent-ft/scripts/replay_eval.py"],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stderr or completed.stdout

    sft_report = json.loads((PROJECT_ROOT / "outputs" / "reports" / "sft_eval.json").read_text(encoding="utf-8"))
    dpo_report = json.loads((PROJECT_ROOT / "outputs" / "reports" / "dpo_eval.json").read_text(encoding="utf-8"))
    replay_report = json.loads((PROJECT_ROOT / "outputs" / "reports" / "replay_eval.json").read_text(encoding="utf-8"))

    assert sft_report["summary"]["overall_pass_rate"] >= 0.9
    assert dpo_report["summary"]["preference_accuracy"] >= 0.9
    assert replay_report["tuned"]["graph_retrieval_hit_rate"] >= replay_report["baseline"]["graph_retrieval_hit_rate"]
