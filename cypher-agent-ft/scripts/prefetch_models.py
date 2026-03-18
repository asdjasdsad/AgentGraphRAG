from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher-model", default="Qwen/Qwen3-Coder-30B-A3B-Instruct")
    parser.add_argument("--student-model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    args = parser.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer

    for model_name in [args.teacher_model, args.student_model]:
        print(f"prefetch tokenizer: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        print(f"prefetch model: {model_name}")
        AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, device_map="cpu")
        print(f"cached: {model_name}")


if __name__ == "__main__":
    main()
