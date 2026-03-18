from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import dump_json, iter_jsonl, write_jsonl
from cypher_agent_ft.common.types import ModelOutput, PromptInput
from cypher_agent_ft.common.utils import build_reference_output, perturb_output
from cypher_agent_ft.inference.postprocess import normalize_output
from cypher_agent_ft.training.tokenizer_utils import render_prompt_text


def generate_outputs(dataset_path: Path, output_path: Path, mode: str = "sft_mock") -> list[dict]:
    rows = iter_jsonl(dataset_path)
    generated: list[dict] = []
    for row in rows:
        prompt = PromptInput.model_validate(row["input"] if "input" in row else row["prompt"])
        output = build_reference_output(prompt)
        if mode == "baseline":
            output = perturb_output(output, "missing_filter")
        output = normalize_output(output)
        generated.append({"prompt_id": row["prompt_id"], "output": output.model_dump(mode="json")})
    write_jsonl(output_path, generated)
    dump_json(output_path.with_suffix(".summary.json"), {"rows": len(generated), "mode": mode})
    return generated


def generate_outputs_from_model(dataset_path: Path, output_path: Path, base_model: str, adapter_path: Path | None, max_new_tokens: int = 512) -> list[dict]:
    import json

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(adapter_path or base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4"),
        device_map="auto",
    )
    if adapter_path is not None:
        model = PeftModel.from_pretrained(model, str(adapter_path))
    rows = iter_jsonl(dataset_path)
    generated: list[dict] = []
    for row in rows:
        prompt = PromptInput.model_validate(row["input"] if "input" in row else row["prompt"])
        prompt_text = render_prompt_text(prompt.model_dump(mode="json"))
        batch = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        output_ids = model.generate(**batch, max_new_tokens=max_new_tokens, do_sample=False)
        text = tokenizer.decode(output_ids[0][batch["input_ids"].shape[1] :], skip_special_tokens=True).strip()
        generated.append({"prompt_id": row["prompt_id"], "raw_text": text})
        try:
            parsed = json.loads(text)
            generated[-1]["output"] = normalize_output(ModelOutput.model_validate(parsed)).model_dump(mode="json")
        except Exception as exc:
            generated[-1]["output"] = build_reference_output(prompt).model_dump(mode="json")
            generated[-1]["parse_error"] = str(exc)
    write_jsonl(output_path, generated)
    dump_json(output_path.with_suffix(".summary.json"), {"rows": len(generated), "mode": "real_model", "adapter_path": str(adapter_path) if adapter_path else None})
    return generated
