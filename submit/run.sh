#!/bin/bash
set -euo pipefail

echo "=== Fusai submission run.sh ==="
echo "FUSAI_TRACK=${FUSAI_TRACK:-danbaizhi}"
echo "SAISDATA=${SAISDATA:-/saisdata}"
echo "SAISRESULT=${SAISRESULT:-/saisresult}"

if [ -f /app/submit/build_info.json ]; then
  echo "=== build_info.json ==="
  cat /app/submit/build_info.json
fi

if [ -d "${SAISDATA:-/saisdata}" ]; then
  echo "=== saisdata preview (maxdepth 3) ==="
  find "${SAISDATA:-/saisdata}" -maxdepth 3 \( -type f -o -type d \) 2>/dev/null | head -60 || ls -la "${SAISDATA:-/saisdata}" || true
else
  echo "WARNING: SAISDATA path missing: ${SAISDATA:-/saisdata}"
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
fi

python3 /app/submit/main.py \
  --track "${FUSAI_TRACK:-danbaizhi}" \
  --saisdata "${SAISDATA:-/saisdata}" \
  --saisresult "${SAISRESULT:-/saisresult}" \
  --work-dir /app

echo "=== done ==="
