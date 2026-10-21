#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
REQUIREMENTS="${ROOT_DIR}/requirements.txt"

if [[ ! -f "${REQUIREMENTS}" ]]; then
  printf '\033[31m[error]\033[0m Missing requirements.txt in %s\n' "${ROOT_DIR}" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '\033[31m[error]\033[0m Python 3 is required.\n' >&2
  exit 1
fi

printf '\033[36m\n  ◆ Marketing AI Guardrails\033[0m\n'
printf '\033[2m  Preparing isolated Python environment...\033[0m\n\n'

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

PYTHON="${VENV_DIR}/bin/python"

# Textual is installed first so it can display the remaining installation steps.
"${PYTHON}" -m pip install --disable-pip-version-check --quiet 'textual>=0.80'

"${PYTHON}" "${ROOT_DIR}/installer.py" "${REQUIREMENTS}" "${ROOT_DIR}/prompt.txt"
