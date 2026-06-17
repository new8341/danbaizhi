#!/usr/bin/env bash
# Bootstrap ColabFold in WSL (venv under Project/.venv_colabfold).
set -euo pipefail
ROOT="/mnt/h/Fusai/Project"
VENV="$ROOT/.venv_colabfold"
LOG_DIR="$ROOT/processed_data/colabfold/_logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/setup_colabfold_$(date +%Y%m%d%H%M).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== setup_colabfold_wsl $(date -Iseconds) ==="
cd "$ROOT"

if ! command -v python3 >/dev/null; then
  echo "Installing python3-venv pip..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3-pip
fi

if [[ ! -x "$VENV/bin/colabfold_batch" ]]; then
  echo "Creating venv and installing colabfold[alphafold] (may take 15-30 min)..."
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -U pip wheel setuptools
  export JAX_PLATFORMS=cpu
  pip install "colabfold[alphafold]"
else
  echo "colabfold_batch already present: $VENV/bin/colabfold_batch"
fi

"$VENV/bin/colabfold_batch" --help | head -5
echo "=== setup done $(date -Iseconds) ==="
