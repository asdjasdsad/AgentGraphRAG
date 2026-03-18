from __future__ import annotations

import argparse

from _bootstrap import ROOT
from cypher_agent_ft.common.io import iter_jsonl, write_jsonl
from cypher_agent_ft.common.types import PromptInput
from cypher_agent_ft.common.utils import stable_id
from cypher_agent_ft.teacher.client_openai import HuggingFaceTeacherClient, MockTeacherClient, OpenAITeacherClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "openai", "hf-local"], default="mock")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.mode == "mock":
        client = MockTeacherClient()
    elif args.mode == "openai":
        client = OpenAITeacherClient()
    else:
        client = HuggingFaceTeacherClient()
    rows = []
    prompt_rows = list(iter_jsonl(ROOT / "data" / "intermediate" / "prompt_pool.jsonl"))
    if args.limit:
        prompt_rows = prompt_rows[: args.limit]
    for row in prompt_rows:
        prompt = PromptInput.model_validate(row["input"])
        outputs = client.generate_candidates(prompt)
        for index, output in enumerate(outputs):
            rows.append(
                {
                    "candidate_id": stable_id("cand", f"{row['prompt_id']}:{index}"),
                    "prompt_id": row["prompt_id"],
                    "source": args.mode,
                    "input": prompt.model_dump(mode="json"),
                    "output": output.model_dump(mode="json"),
                }
            )
    write_jsonl(ROOT / "data" / "intermediate" / "candidate_pool.jsonl", rows)
    print(f"generated {len(rows)} candidates")


if __name__ == "__main__":
    main()
