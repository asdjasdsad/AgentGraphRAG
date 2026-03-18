#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GPU_ID="${GPU_ID:-0}"
PROMPT_LIMIT="${PROMPT_LIMIT:-500}"
TEACHER_MODEL="${TEACHER_MODEL:-Qwen/Qwen3-Coder-30B-A3B-Instruct}"
MAX_PROMPT_LIMIT_SMOKE="${MAX_PROMPT_LIMIT_SMOKE:-5}"

cd "${ROOT_DIR}"

python cypher-agent-ft/scripts/export_schema.py
python cypher-agent-ft/scripts/build_prompt_pool.py --limit "${PROMPT_LIMIT}"
CUDA_VISIBLE_DEVICES="${GPU_ID}" HF_TEACHER_MODEL="${TEACHER_MODEL}" \
  python cypher-agent-ft/scripts/generate_candidates_gpt4o.py --mode hf-local
python cypher-agent-ft/scripts/validate_candidates.py
python cypher-agent-ft/scripts/build_sft_dataset.py
python cypher-agent-ft/scripts/generate_sft_outputs.py --mode sft_mock --split test
python cypher-agent-ft/scripts/build_dpo_dataset.py

echo "data pipeline finished"
echo "teacher=${TEACHER_MODEL}"
echo "tip: first smoke test with: CUDA_VISIBLE_DEVICES=${GPU_ID} HF_TEACHER_MODEL=${TEACHER_MODEL} python cypher-agent-ft/scripts/generate_candidates_gpt4o.py --mode hf-local --limit ${MAX_PROMPT_LIMIT_SMOKE}"
