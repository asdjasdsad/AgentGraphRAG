from __future__ import annotations

import argparse

from _bootstrap import ROOT
from cypher_agent_ft.inference.generate import generate_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "sft_mock", "dpo_mock"], default="sft_mock")
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    args = parser.parse_args()
    generate_outputs(ROOT / "data" / "sft" / f"{args.split}.jsonl", ROOT / "data" / "processed" / f"{args.mode}_{args.split}_predictions.jsonl", mode=args.mode)
    print(f"generated predictions for {args.mode}")


if __name__ == "__main__":
    main()
