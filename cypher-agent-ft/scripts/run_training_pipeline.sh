#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GPU_ID="${GPU_ID:-0}"

cd "${ROOT_DIR}"

CUDA_VISIBLE_DEVICES="${GPU_ID}" python cypher-agent-ft/scripts/train_real.py --stage sft
CUDA_VISIBLE_DEVICES="${GPU_ID}" python cypher-agent-ft/scripts/train_real.py --stage dpo
CUDA_VISIBLE_DEVICES="${GPU_ID}" python cypher-agent-ft/scripts/generate_real_outputs.py \
  --dataset cypher-agent-ft/data/sft/test.jsonl \
  --adapter-path cypher-agent-ft/outputs/adapters/dpo-real \
  --output cypher-agent-ft/data/processed/dpo_real_predictions.jsonl

echo "training pipeline finished"
