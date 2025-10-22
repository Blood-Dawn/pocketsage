#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python}
if [ -n "${PIP:-}" ]; then
  mapfile -d '' -t PIP_CMD < <(PIP_VALUE="$PIP" "$PYTHON" - <<'PY'
import os
import shlex
pip = os.environ["PIP_VALUE"]
for part in shlex.split(pip):
    print(part, end="\0")
PY
  )
else
  PIP_CMD=("$PYTHON" -m pip)
fi

"${PIP_CMD[@]}" install --upgrade pip
"${PIP_CMD[@]}" install -e ".[dev]"
pre-commit install
