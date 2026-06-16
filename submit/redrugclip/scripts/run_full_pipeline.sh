#!/bin/bash
# Full competition pipeline (Linux/macOS)
set -e
cd "$(dirname "$0")/.."
python scripts/run_agent.py "$@"
