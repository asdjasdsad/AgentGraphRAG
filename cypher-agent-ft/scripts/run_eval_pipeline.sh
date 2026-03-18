#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "${ROOT_DIR}"

python cypher-agent-ft/scripts/eval_offline.py --stage sft
python cypher-agent-ft/scripts/eval_offline.py --stage dpo
python cypher-agent-ft/scripts/replay_eval.py

echo "evaluation pipeline finished"
