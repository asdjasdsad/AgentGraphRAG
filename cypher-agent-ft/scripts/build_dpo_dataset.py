from __future__ import annotations

from collections import Counter, defaultdict

from _bootstrap import ROOT
from cypher_agent_ft.common.io import iter_jsonl, write_jsonl
from cypher_agent_ft.common.types import SFTRecord
from cypher_agent_ft.datasets.dpo_builder import build_dpo_records


def main() -> None:
    rejected_pool: dict[str, list[dict]] = defaultdict(list)
    for row in iter_jsonl(ROOT / "data" / "processed" / "validated_candidates.jsonl"):
        if not row["validation"]["passed"]:
            rejected_pool[row["prompt_id"]].append(row["output"])
    for row in iter_jsonl(ROOT / "data" / "processed" / "sft_mock_test_predictions.jsonl"):
        rejected_pool[row["prompt_id"]].append(row["output"])
    sft_rows = [SFTRecord.model_validate(row) for row in iter_jsonl(ROOT / "data" / "sft" / "all.jsonl")]
    rows = [item.model_dump(mode="json") for item in build_dpo_records(sft_rows, rejected_pool)]
    write_jsonl(ROOT / "data" / "dpo" / "all.jsonl", rows)
    for split in ("train", "val", "test"):
        write_jsonl(ROOT / "data" / "dpo" / f"{split}.jsonl", [row for row in rows if row["split"] == split])
    print(f"dpo rows: {Counter(row['split'] for row in rows)}")


if __name__ == "__main__":
    main()
