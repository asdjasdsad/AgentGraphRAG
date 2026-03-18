from __future__ import annotations

import argparse

from _bootstrap import ROOT
from cypher_agent_ft.eval.offline_eval import evaluate_predictions
from cypher_agent_ft.inference.generate import generate_outputs
from cypher_agent_ft.schema.loader import load_schema
from cypher_agent_ft.training.dpo_runner import run_dpo
from cypher_agent_ft.training.sft_runner import run_sft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["sft", "dpo"], default="sft")
    args = parser.parse_args()
    schema = load_schema(ROOT / "configs" / "schema.yaml")
    if args.stage == "sft":
        run_sft(ROOT / "configs" / "sft.yaml", ROOT / "data" / "sft" / "all.jsonl", ROOT / "outputs" / "adapters" / "sft")
        dataset = ROOT / "data" / "sft" / "test.jsonl"
        predictions = ROOT / "data" / "processed" / "sft_test_predictions.jsonl"
        generate_outputs(dataset, predictions, mode="sft_mock")
        report = ROOT / "outputs" / "reports" / "sft_eval.json"
        evaluate_predictions(schema, dataset, predictions, report)
    else:
        run_dpo(ROOT / "configs" / "dpo.yaml", ROOT / "data" / "dpo" / "all.jsonl", ROOT / "outputs" / "adapters" / "dpo")
        dataset = ROOT / "data" / "dpo" / "test.jsonl"
        predictions = ROOT / "data" / "processed" / "dpo_test_predictions.jsonl"
        generate_outputs(dataset, predictions, mode="dpo_mock")
        report = ROOT / "outputs" / "reports" / "dpo_eval.json"
        evaluate_predictions(schema, dataset, predictions, report, include_preference=True)
    print(f"wrote {report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
