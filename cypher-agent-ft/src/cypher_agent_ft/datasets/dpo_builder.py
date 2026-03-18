from __future__ import annotations

from collections import defaultdict

from cypher_agent_ft.common.types import DPORecord, ModelOutput, SFTRecord
from cypher_agent_ft.common.utils import perturb_output


def synthesize_hard_negatives(chosen: ModelOutput) -> list[ModelOutput]:
    return [
        perturb_output(chosen, "missing_filter"),
        perturb_output(chosen, "bad_return"),
        perturb_output(chosen, "hop_error"),
    ]


def build_dpo_records(sft_rows: list[SFTRecord], rejected_pool: dict[str, list[dict]]) -> list[DPORecord]:
    rows: list[DPORecord] = []
    for item in sft_rows:
        chosen = ModelOutput.model_validate(item.output)
        prompt_id = item.prompt_id
        rejected_candidates = [ModelOutput.model_validate(entry) for entry in rejected_pool.get(prompt_id, [])]
        rejected_candidates.extend(synthesize_hard_negatives(chosen))
        if not rejected_candidates:
            continue
        for rejected in rejected_candidates[:2]:
            rows.append(
                DPORecord(
                    prompt_id=prompt_id,
                    prompt=item.input,
                    chosen=chosen.model_dump(mode="json"),
                    rejected=rejected.model_dump(mode="json"),
                    split=item.split,
                    metadata={"chosen_source": item.metadata.get("candidate_id", "sft_gold")},
                )
            )
    return rows
