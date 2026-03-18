from __future__ import annotations

from collections import Counter

from _bootstrap import ROOT
from cypher_agent_ft.common.io import iter_jsonl, write_jsonl
from cypher_agent_ft.common.types import CandidateRecord
from cypher_agent_ft.datasets.sft_builder import build_sft_records


def main() -> None:
    candidates = [CandidateRecord.model_validate(row) for row in iter_jsonl(ROOT / "data" / "processed" / "validated_candidates.jsonl")]
    rows = [item.model_dump(mode="json") for item in build_sft_records(candidates)]
    write_jsonl(ROOT / "data" / "sft" / "all.jsonl", rows)
    for split in ("train", "val", "test"):
        write_jsonl(ROOT / "data" / "sft" / f"{split}.jsonl", [row for row in rows if row["split"] == split])
    print(f"sft rows: {Counter(row['split'] for row in rows)}")


if __name__ == "__main__":
    main()
