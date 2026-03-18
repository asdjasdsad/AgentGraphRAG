from __future__ import annotations

from _bootstrap import ROOT
from cypher_agent_ft.eval.replay_eval import evaluate_replay
from cypher_agent_ft.inference.generate import generate_outputs
from cypher_agent_ft.schema.loader import load_schema


def main() -> None:
    schema = load_schema(ROOT / "configs" / "schema.yaml")
    replay_path = ROOT / "data" / "raw" / "replay_queries.jsonl"
    baseline_predictions = ROOT / "data" / "processed" / "replay_baseline_predictions.jsonl"
    tuned_predictions = ROOT / "data" / "processed" / "replay_tuned_predictions.jsonl"
    generate_outputs(replay_path, baseline_predictions, mode="baseline")
    generate_outputs(replay_path, tuned_predictions, mode="dpo_mock")
    report = evaluate_replay(schema, replay_path, baseline_predictions, tuned_predictions, ROOT / "outputs" / "reports" / "replay_eval.json")
    print(report)


if __name__ == "__main__":
    main()
