from __future__ import annotations

from cypher_agent_ft.common.types import ModelOutput, PromptInput, SFTRecord


INSTRUCTION = "根据给定的结构化问题、图谱 Schema 上下文和查询约束，生成 query_plan 和可执行的 Cypher。"


def format_sft_record(prompt_id: str, prompt: PromptInput, output: ModelOutput, split: str, metadata: dict) -> SFTRecord:
    return SFTRecord(
        prompt_id=prompt_id,
        instruction=INSTRUCTION,
        input=prompt.model_dump(mode="json"),
        output=output.model_dump(mode="json"),
        split=split,
        metadata=metadata,
    )
