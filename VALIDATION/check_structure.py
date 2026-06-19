#!/usr/bin/env python3
"""Validate competition framework directory layout."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "GOVERNANCE/PROJECT_RULES.md",
    "GOVERNANCE/MODES.md",
    "GOVERNANCE/DEVELOPMENT_RULES.md",
    "GOVERNANCE/SUBMISSION_RULES.md",
    "INDEX/PROJECT_INDEX.md",
    "INDEX/RESOURCE_INDEX.md",
    "STATUS/DAILY_STATUS.md",
    "STATUS/SCOREBOARD.md",
    "SUBMISSIONS/README.md",
    "submit/track_pins.json",
    "scripts/archive_competition.py",
    "scripts/generate_scoreboard.py",
]

TRACKS = ("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi")
TRACK_FILES = ("REQUIREMENTS.md", "SUBMISSION_SPEC.md", "EXPERIMENTS.md", "LESSONS_LEARNED.md")


def main() -> int:
    missing: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            missing.append(rel)
    for track in TRACKS:
        for name in TRACK_FILES:
            rel = f"TASKS/{track}/{name}"
            if not (ROOT / rel).is_file():
                missing.append(rel)
    if missing:
        print("check_structure: FAIL", file=sys.stderr)
        for m in missing:
            print(f"  missing: {m}", file=sys.stderr)
        return 1
    print(f"check_structure: OK ({len(REQUIRED) + len(TRACKS) * len(TRACK_FILES)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
