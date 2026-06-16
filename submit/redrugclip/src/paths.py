"""Project path constants. document/ is read-only per competition rules."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BENCHMARK_ENV = os.environ.get("BENCHMARK_ROOT", "")
BENCHMARK_ROOT = (
    Path(_BENCHMARK_ENV) if _BENCHMARK_ENV else PROJECT_ROOT / "document" / "benchmark"
)
MANIFEST_PATH = BENCHMARK_ROOT / "manifest.jsonl"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DAIMA_DIR = PROJECT_ROOT / "daima"
CONFIGS_DIR = PROJECT_ROOT / "configs"

# Directories copied into daima/ on each archived run (exclude document/)
ARCHIVE_CODE_DIRS = ("src", "agent", "configs", "scripts")
ARCHIVE_ROOT_FILES = ("requirements.txt", "readme.md", "README.md", "run.sh", "run.bat")
