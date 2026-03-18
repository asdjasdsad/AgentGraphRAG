from __future__ import annotations

from pathlib import Path

from cypher_agent_ft.common.io import dump_json, iter_jsonl, load_config
from cypher_agent_ft.common.types import TrainingArtifact
from cypher_agent_ft.training.tokenizer_utils import render_prompt_text


def _torch_dtype(name: str):
    import torch

    return {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}.get(name, torch.bfloat16)


def run_dpo(config_path: Path, dataset_path: Path, output_dir: Path) -> TrainingArtifact:
    config = load_config(config_path)
    rows = iter_jsonl(dataset_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = TrainingArtifact(
        stage="dpo",
        backend=config.get("backend", "mock"),
        base_model=config["base_model"],
        dataset_path=str(dataset_path),
        output_dir=str(output_dir),
        metrics={"train_rows": len([row for row in rows if row["split"] == "train"]), "val_rows": len([row for row in rows if row["split"] == "val"])},
        command=["mock_dpo_runner", "--config", str(config_path), "--dataset", str(dataset_path)],
    )
    dump_json(output_dir / "training_manifest.json", artifact.model_dump(mode="json"))
    dump_json(output_dir / "best_checkpoint.json", {"checkpoint": "mock-dpo-best", "stage": "dpo"})
    return artifact


def run_dpo_real(config_path: Path, dataset_path: Path, sft_adapter_dir: Path, output_dir: Path) -> TrainingArtifact:
    import json

    from datasets import Dataset
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer

    config = load_config(config_path)
    rows = iter_jsonl(dataset_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    quantization_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=_torch_dtype("bf16"))
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base_model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        trust_remote_code=True,
        quantization_config=quantization_config,
        device_map="auto",
    )
    model = PeftModel.from_pretrained(base_model, str(sft_adapter_dir), is_trainable=True)
    ref_model = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            config["base_model"],
            trust_remote_code=True,
            quantization_config=quantization_config,
            device_map="auto",
        ),
        str(sft_adapter_dir),
        is_trainable=False,
    )

    def format_row(row: dict) -> dict:
        return {
            "prompt": render_prompt_text(row["prompt"]),
            "chosen": json.dumps(row["chosen"], ensure_ascii=False, indent=2),
            "rejected": json.dumps(row["rejected"], ensure_ascii=False, indent=2),
        }

    train_rows = [format_row(row) for row in rows if row["split"] == "train"]
    val_rows = [format_row(row) for row in rows if row["split"] == "val"]
    train_ds = Dataset.from_list(train_rows)
    eval_ds = Dataset.from_list(val_rows) if val_rows else None
    training = config["training"]
    args = DPOConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=training["per_device_train_batch_size"],
        per_device_eval_batch_size=training.get("per_device_eval_batch_size", training["per_device_train_batch_size"]),
        gradient_accumulation_steps=training["gradient_accumulation_steps"],
        learning_rate=training["learning_rate"],
        num_train_epochs=training["num_train_epochs"],
        beta=training["beta"],
        logging_steps=training.get("logging_steps", 5),
        eval_strategy="steps" if eval_ds is not None else "no",
        eval_steps=training.get("eval_steps", 20) if eval_ds is not None else None,
        save_steps=training.get("save_steps", training.get("eval_steps", 20)),
        bf16=training.get("bf16", True),
        report_to=[],
        max_length=training["max_seq_length"],
        max_prompt_length=training.get("max_prompt_length", 2048),
        remove_unused_columns=False,
    )
    trainer = DPOTrainer(
        model=model,
        ref_model=ref_model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(output_dir)
    metrics = dict(trainer.state.log_history[-1]) if trainer.state.log_history else {}
    artifact = TrainingArtifact(
        stage="dpo",
        backend="trl-dpo",
        base_model=config["base_model"],
        dataset_path=str(dataset_path),
        output_dir=str(output_dir),
        metrics={
            "train_rows": len(train_rows),
            "val_rows": len(val_rows),
            "trainer_metrics": metrics,
            "sft_adapter_dir": str(sft_adapter_dir),
        },
        command=["python", "cypher-agent-ft/scripts/train_real.py", "--stage", "dpo"],
    )
    dump_json(output_dir / "training_manifest.json", artifact.model_dump(mode="json"))
    dump_json(output_dir / "best_checkpoint.json", {"checkpoint": str(output_dir), "stage": "dpo"})
    return artifact
