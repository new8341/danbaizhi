#!/bin/bash
# Build (and optionally push) a Fusai track docker image.
# Usage: sh docker_build.sh <track> <registry/image:tag> [--push]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TRACK="${1:-}"
IMAGE="${2:-}"
PUSH="${3:-}"

if [ -z "$TRACK" ] || [ -z "$IMAGE" ]; then
  echo "Usage: sh submit/docker_build.sh <track> <registry/image:tag> [--push]"
  echo "Tracks: danbaizhi | drugclip | baxiangfenzi | shenjingsuanzi"
  echo "Example: sh submit/docker_build.sh danbaizhi registry.cn-shenzhen.aliyuncs.com/ns/fusai:0.1"
  exit 1
fi

DOCKERFILE="$ROOT/submit/Dockerfile.${TRACK}"
if [ ! -f "$DOCKERFILE" ]; then
  echo "Unknown track: $TRACK (missing $DOCKERFILE)"
  exit 1
fi

docker build -f "$DOCKERFILE" -t "$IMAGE" "$ROOT"

echo "Built: $IMAGE (track=$TRACK)"
case "$TRACK" in
  danbaizhi)
    echo "Local test:"
    echo "  docker run --rm -v \"$ROOT/documen/Danbaizhi:/saisdata:ro\" -v \"$ROOT/submit/_local_saisresult:/saisresult\" -e FUSAI_TRACK=danbaizhi $IMAGE"
    ;;
  drugclip)
    echo "Local test:"
    echo "  docker run --rm -v \"$ROOT/submit/_local_saisresult:/saisresult\" -e FUSAI_TRACK=drugclip $IMAGE"
    ;;
  baxiangfenzi)
    echo "Local test:"
    echo "  docker run --rm -v \"$ROOT/documen/Baxiangfenzi:/saisdata:ro\" -v \"$ROOT/submit/_local_saisresult:/saisresult\" -e FUSAI_TRACK=baxiangfenzi $IMAGE"
    ;;
  shenjingsuanzi)
    echo "Local test:"
    echo "  docker run --rm -v \"$ROOT/documen/Shenjingsuanzi:/saisdata:ro\" -v \"$ROOT/submit/_local_saisresult:/saisresult\" -e FUSAI_TRACK=shenjingsuanzi $IMAGE"
    ;;
esac

if [ "$PUSH" = "--push" ]; then
  docker push "$IMAGE"
  echo "Pushed: $IMAGE"
fi
