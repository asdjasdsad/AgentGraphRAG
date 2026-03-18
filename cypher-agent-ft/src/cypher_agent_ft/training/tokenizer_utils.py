from __future__ import annotations

import json
from dataclasses import dataclass

from cypher_agent_ft.datasets.formatter import INSTRUCTION


def render_prompt_text(prompt: dict) -> str:
    return f"{INSTRUCTION}\n\n输入:\n{json.dumps(prompt, ensure_ascii=False, indent=2)}\n\n输出:\n"


def render_training_example(prompt: dict, output: dict) -> str:
    return render_prompt_text(prompt) + json.dumps(output, ensure_ascii=False, indent=2)


def tokenize_for_local_runner(prompt: dict, output: dict) -> dict[str, list[int]]:
    text = render_training_example(prompt, output)
    tokens = text.split()
    token_ids = list(range(1, len(tokens) + 1))
    return {"input_ids": token_ids, "attention_mask": [1] * len(token_ids), "labels": token_ids[:]}


@dataclass
class SupervisedDataCollator:
    tokenizer: object
    max_length: int

    def __call__(self, features: list[dict]) -> dict:
        import torch

        input_ids = [torch.tensor(item["input_ids"][: self.max_length], dtype=torch.long) for item in features]
        attention_mask = [torch.tensor(item["attention_mask"][: self.max_length], dtype=torch.long) for item in features]
        labels = [torch.tensor(item["labels"][: self.max_length], dtype=torch.long) for item in features]
        input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=self.tokenizer.pad_token_id)
        attention_mask = torch.nn.utils.rnn.pad_sequence(attention_mask, batch_first=True, padding_value=0)
        labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def tokenize_supervised_example(tokenizer, prompt: dict, output: dict, max_length: int) -> dict[str, list[int]]:
    prompt_text = render_prompt_text(prompt)
    full_text = prompt_text + json.dumps(output, ensure_ascii=False, indent=2)
    prompt_tokens = tokenizer(prompt_text, add_special_tokens=False)
    full_tokens = tokenizer(full_text, add_special_tokens=False, truncation=True, max_length=max_length)
    input_ids = full_tokens["input_ids"]
    attention_mask = full_tokens["attention_mask"]
    prompt_len = min(len(prompt_tokens["input_ids"]), len(input_ids))
    labels = [-100] * prompt_len + input_ids[prompt_len:]
    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}
