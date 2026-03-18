from __future__ import annotations

import json
import os

import httpx

from cypher_agent_ft.common.types import ModelOutput, PromptInput
from cypher_agent_ft.common.utils import build_reference_output, perturb_output
from cypher_agent_ft.teacher.prompt_builder import build_teacher_prompt


class MockTeacherClient:
    def generate_candidates(self, prompt: PromptInput) -> list[ModelOutput]:
        gold = build_reference_output(prompt)
        return [
            gold,
            perturb_output(gold, "missing_filter"),
            perturb_output(gold, "reverse_relation"),
        ]


class OpenAITeacherClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o"

    def generate_candidates(self, prompt: PromptInput) -> list[ModelOutput]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai mode")
        messages = [
            {"role": "system", "content": "You generate Cypher query plans for graph reasoning tasks and must return strict JSON."},
            {"role": "user", "content": build_teacher_prompt(prompt)},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "n": 3,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        outputs: list[ModelOutput] = []
        for choice in body.get("choices", []):
            content = choice.get("message", {}).get("content", "{}")
            outputs.append(ModelOutput.model_validate_json(content))
        if not outputs:
            raise RuntimeError("OpenAI returned no candidates")
        return outputs


class HuggingFaceTeacherClient:
    def __init__(
        self,
        model: str | None = None,
        max_new_tokens: int = 768,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_return_sequences: int = 3,
    ) -> None:
        self.model_name = model or os.getenv("HF_TEACHER_MODEL") or "Qwen/Qwen3-Coder-30B-A3B-Instruct"
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.num_return_sequences = num_return_sequences
        self._tokenizer = None
        self._model = None

    def _load(self):
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            ),
            device_map="auto",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )
        return self._model, self._tokenizer

    def _extract_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("No JSON object found in model output")

    def generate_candidates(self, prompt: PromptInput) -> list[ModelOutput]:
        model, tokenizer = self._load()
        system_prompt = "You generate Cypher query plans for graph reasoning tasks and must return strict JSON with keys query_plan and cypher."
        user_prompt = build_teacher_prompt(prompt)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        batch = tokenizer(text, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **batch,
            max_new_tokens=self.max_new_tokens,
            do_sample=True,
            temperature=self.temperature,
            top_p=self.top_p,
            num_return_sequences=self.num_return_sequences,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
        prompt_len = batch["input_ids"].shape[1]
        candidates: list[ModelOutput] = []
        for sequence in outputs:
            decoded = tokenizer.decode(sequence[prompt_len:], skip_special_tokens=True).strip()
            try:
                candidates.append(ModelOutput.model_validate(self._extract_json(decoded)))
            except Exception:
                continue
        if not candidates:
            gold = build_reference_output(prompt)
            return [gold, perturb_output(gold, "missing_filter"), perturb_output(gold, "reverse_relation")]
        return candidates[: self.num_return_sequences]
