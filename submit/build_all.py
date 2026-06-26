#!/usr/bin/env python3
"""Build (and optionally push) all track docker images from one repo."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMIT = ROOT / "submit"

sys.path.insert(0, str(ROOT))

from submit.registry_config import TRACKS, image_ref, load_registry_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build all Fusai track docker images")
    p.add_argument("--tag", help="Image tag (default: from registry.env or 0.1)")
    p.add_argument("--tracks", nargs="+", choices=TRACKS, default=list(TRACKS))
    p.add_argument("--push", action="store_true", help="Push images after build")
    p.add_argument("--dry-run", action="store_true", help="Print commands only")
    return p.parse_args()


def build_track(track: str, tag: str | None, push: bool, dry_run: bool) -> int:
    dockerfile = SUBMIT / f"Dockerfile.{track}"
    if not dockerfile.is_file():
        print(f"[SKIP] missing {dockerfile}", file=sys.stderr)
        return 1
    ignorefile = ROOT / f".dockerignore.{track}"
    ref = image_ref(track, tag=tag)
    build_cmd = ["docker", "build"]
    if ignorefile.is_file():
        build_cmd += ["--ignorefile", str(ignorefile)]
    build_cmd += ["-f", str(dockerfile), "-t", ref, str(ROOT)]
    print(f"[BUILD] {track} -> {ref}")
    if dry_run:
        print(" ", " ".join(build_cmd))
        if push:
            print(" ", "docker", "push", ref)
        return 0
    subprocess.run(build_cmd, check=True)
    if push:
        print(f"[PUSH] {ref}")
        subprocess.run(["docker", "push", ref], check=True)
    return 0


def main() -> int:
    args = parse_args()
    cfg = load_registry_env()
    tag = args.tag or cfg["TAG"]
    print(f"Registry={cfg['REGISTRY']} namespace={cfg['NAMESPACE']} tag={tag}")
    rc = 0
    for track in args.tracks:
        rc |= build_track(track, tag, args.push, args.dry_run)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
