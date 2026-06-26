#!/bin/bash
# Build all Fusai track images.
# Usage:
#   sh submit/build_all.sh
#   sh submit/build_all.sh 0.2 --push
#   sh submit/build_all.sh 0.1 danbaizhi drugclip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-}"
shift || true

PUSH=""
TRACKS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --push) PUSH="--push"; shift ;;
    --dry-run) DRY="--dry-run"; shift ;;
    *) TRACKS+=("$1"); shift ;;
  esac
done

CMD=(python3 "$ROOT/submit/build_all.py")
[ -n "$TAG" ] && CMD+=(--tag "$TAG")
[ -n "$PUSH" ] && CMD+=("$PUSH")
[ -n "${DRY:-}" ] && CMD+=("$DRY")
[ ${#TRACKS[@]} -gt 0 ] && CMD+=(--tracks "${TRACKS[@]}")

cd "$ROOT"
exec "${CMD[@]}"
