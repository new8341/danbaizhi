#!/bin/bash
set -euo pipefail

echo "=== Fusai submission run.sh ==="
echo "FUSAI_TRACK=${FUSAI_TRACK:-danbaizhi}"
echo "SAISDATA=${SAISDATA:-/saisdata}"
echo "SAISRESULT=${SAISRESULT:-/saisresult}"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
fi

python3 /app/submit/main.py \
  --track "${FUSAI_TRACK:-danbaizhi}" \
  --saisdata "${SAISDATA:-/saisdata}" \
  --saisresult "${SAISRESULT:-/saisresult}" \
  --work-dir /app

echo "=== done ==="
