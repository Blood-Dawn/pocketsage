#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python}
if [ -n "${PIP:-}" ]; then
  # shellcheck disable=SC2206
  PIP_CMD=($PIP)
else
  PIP_CMD=("$PYTHON" -m pip)
fi

"${PIP_CMD[@]}" install --upgrade pip
"${PIP_CMD[@]}" install -e ".[dev]"
pre-commit install
