#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-cypher-agent-ft"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/4] create venv at ${VENV_DIR}"
if [[ ! -d "${VENV_DIR}" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

echo "[2/4] upgrade pip"
python -m pip install --upgrade pip setuptools wheel

echo "[3/4] install main project deps"
python -m pip install -r "${ROOT_DIR}/requirements.txt"

echo "[4/4] install cypher-agent-ft locked deps"
python -m pip install -r "${ROOT_DIR}/cypher-agent-ft/requirements.lock.txt"

echo "bootstrap finished"
echo "activate with: source ${VENV_DIR}/bin/activate"
