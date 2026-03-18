from __future__ import annotations

from collections import defaultdict

from cypher_agent_ft.common.types import CandidateRecord, SFTRecord
from cypher_agent_ft.common.utils import deterministic_split
from cypher_agent_ft.datasets.formatter import format_sft_record


def build_sft_records(candidates: list[CandidateRecord]) -> list[SFTRecord]:
    grouped: dict[str, list[CandidateRecord]] = defaultdict(list)
    for item in candidates:
        grouped[item.prompt_id].append(item)
    rows: list[SFTRecord] = []
    for prompt_id, prompt_candidates in grouped.items():
        valid = [item for item in prompt_candidates if item.validation.passed]
        if not valid:
            continue
        best = sorted(valid, key=lambda item: item.validation.score, reverse=True)[0]
        rows.append(
            format_sft_record(
                prompt_id=prompt_id,
                prompt=best.input,
                output=best.output,
                split=deterministic_split(prompt_id),
                metadata={"candidate_id": best.candidate_id, "score": best.validation.score},
            )
        )
    return rows
