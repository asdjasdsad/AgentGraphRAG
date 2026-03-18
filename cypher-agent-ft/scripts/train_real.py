from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import ROOT
from cypher_agent_ft.training.dpo_runner import run_dpo_real
from cypher_agent_ft.training.sft_runner import run_sft_real


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["sft", "dpo"], required=True)
    parser.add_argument("--sft-config", default=str(ROOT / "configs" / "sft.yaml"))
    parser.add_argument("--dpo-config", default=str(ROOT / "configs" / "dpo.yaml"))
    parser.add_argument("--sft-dataset", default=str(ROOT / "data" / "sft" / "all.jsonl"))
    parser.add_argument("--dpo-dataset", default=str(ROOT / "data" / "dpo" / "all.jsonl"))
    parser.add_argument("--sft-output", default=str(ROOT / "outputs" / "adapters" / "sft-real"))
    parser.add_argument("--dpo-output", default=str(ROOT / "outputs" / "adapters" / "dpo-real"))
    parser.add_argument("--sft-adapter", default=str(ROOT / "outputs" / "adapters" / "sft-real"))
    args = parser.parse_args()

    if args.stage == "sft":
        artifact = run_sft_real(Path(args.sft_config), Path(args.sft_dataset), Path(args.sft_output))
    else:
        artifact = run_dpo_real(Path(args.dpo_config), Path(args.dpo_dataset), Path(args.sft_adapter), Path(args.dpo_output))
    print(artifact.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
