from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import ROOT
from cypher_agent_ft.inference.generate import generate_outputs_from_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "data" / "sft" / "test.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "data" / "processed" / "real_model_predictions.jsonl"))
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--adapter-path")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()
    generate_outputs_from_model(
        Path(args.dataset),
        Path(args.output),
        args.base_model,
        Path(args.adapter_path) if args.adapter_path else None,
        args.max_new_tokens,
    )
    print(args.output)


if __name__ == "__main__":
    main()
