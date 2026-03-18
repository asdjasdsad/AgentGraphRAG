from __future__ import annotations

import json
from pathlib import Path

from cypher_agent_ft.common.io import dump_json, iter_jsonl, load_config
from cypher_agent_ft.common.types import TrainingArtifact
from cypher_agent_ft.training.tokenizer_utils import SupervisedDataCollator, tokenize_supervised_example


def _torch_dtype(name: str):
    import torch

    return {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}.get(name, torch.bfloat16)


def _load_model_and_tokenizer(config: dict):
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = config.get("quantization", {})
    model_kwargs = {"trust_remote_code": True}
    if quant.get("load_in_4bit", False):
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=quant.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_compute_dtype=_torch_dtype(quant.get("bnb_4bit_compute_dtype", "bf16")),
        )
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = _torch_dtype(config.get("torch_dtype", "bf16"))
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["base_model"], **model_kwargs)
    if quant.get("load_in_4bit", False):
        model = prepare_model_for_kbit_training(model)
    lora = config["lora"]
    peft_config = LoraConfig(
        r=lora["r"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=lora["target_modules"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model, tokenizer


def _build_datasets(tokenizer, dataset_path: Path, max_length: int):
    from datasets import Dataset

    rows = iter_jsonl(dataset_path)
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "val"]

    def encode(row: dict) -> dict:
        return tokenize_supervised_example(tokenizer, row["input"], row["output"], max_length)

    train_ds = Dataset.from_list(train_rows).map(encode)
    eval_ds = Dataset.from_list(val_rows).map(encode) if val_rows else None
    return rows, train_ds, eval_ds


def run_sft(config_path: Path, dataset_path: Path, output_dir: Path) -> TrainingArtifact:
    config = load_config(config_path)
    rows = iter_jsonl(dataset_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = TrainingArtifact(
        stage="sft",
        backend=config.get("backend", "mock"),
        base_model=config["base_model"],
        dataset_path=str(dataset_path),
        output_dir=str(output_dir),
        metrics={"train_rows": len([row for row in rows if row["split"] == "train"]), "val_rows": len([row for row in rows if row["split"] == "val"])},
        command=["mock_sft_runner", "--config", str(config_path), "--dataset", str(dataset_path)],
    )
    dump_json(output_dir / "training_manifest.json", artifact.model_dump(mode="json"))
    dump_json(output_dir / "best_checkpoint.json", {"checkpoint": "mock-sft-best", "stage": "sft"})
    return artifact


def run_sft_real(config_path: Path, dataset_path: Path, output_dir: Path) -> TrainingArtifact:
    from transformers import Trainer, TrainingArguments

    config = load_config(config_path)
    training = config["training"]
    output_dir.mkdir(parents=True, exist_ok=True)
    model, tokenizer = _load_model_and_tokenizer(config)
    rows, train_ds, eval_ds = _build_datasets(tokenizer, dataset_path, training["max_seq_length"])
    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=training["per_device_train_batch_size"],
        per_device_eval_batch_size=training.get("per_device_eval_batch_size", training["per_device_train_batch_size"]),
        gradient_accumulation_steps=training["gradient_accumulation_steps"],
        learning_rate=training["learning_rate"],
        num_train_epochs=training["num_train_epochs"],
        logging_steps=training.get("logging_steps", 5),
        save_strategy="steps",
        save_steps=training.get("save_steps", training["eval_steps"]),
        eval_strategy="steps" if eval_ds is not None else "no",
        eval_steps=training["eval_steps"] if eval_ds is not None else None,
        bf16=training.get("bf16", True),
        fp16=training.get("fp16", False),
        gradient_checkpointing=training.get("gradient_checkpointing", True),
        lr_scheduler_type=training.get("lr_scheduler_type", "cosine"),
        warmup_ratio=training.get("warmup_ratio", 0.03),
        report_to=[],
        load_best_model_at_end=eval_ds is not None,
        save_total_limit=training.get("save_total_limit", 2),
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=SupervisedDataCollator(tokenizer, training["max_seq_length"]),
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(output_dir)
    metrics = dict(trainer.state.log_history[-1]) if trainer.state.log_history else {}
    artifact = TrainingArtifact(
        stage="sft",
        backend="transformers-peft",
        base_model=config["base_model"],
        dataset_path=str(dataset_path),
        output_dir=str(output_dir),
        metrics={
            "train_rows": len([row for row in rows if row["split"] == "train"]),
            "val_rows": len([row for row in rows if row["split"] == "val"]),
            "trainer_metrics": metrics,
        },
        command=["python", "cypher-agent-ft/scripts/train_real.py", "--stage", "sft"],
    )
    dump_json(output_dir / "training_manifest.json", artifact.model_dump(mode="json"))
    dump_json(output_dir / "best_checkpoint.json", {"checkpoint": str(output_dir), "stage": "sft"})
    return artifact
