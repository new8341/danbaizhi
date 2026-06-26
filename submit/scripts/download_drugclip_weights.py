#!/usr/bin/env python3
"""Download DrugCLIP benchmark weights from Hugging Face (build-time)."""
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

WEIGHTS = {
    "dude_identity_90.pt": (
        "https://huggingface.co/datasets/THU-ATOM/DrugCLIP_data/"
        "resolve/main/benchmark_weights/dude_identity_90.pt"
    ),
    "litpcba_identity_90.pt": (
        "https://huggingface.co/datasets/THU-ATOM/DrugCLIP_data/"
        "resolve/main/benchmark_weights/litpcba_identity_90.pt"
    ),
}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"skip existing {dest} ({dest.stat().st_size} bytes)")
        return
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved {dest} ({dest.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/app/weights")
    parser.add_argument("--link-as", default="checkpoint_best.pt")
    args = parser.parse_args()
    out = Path(args.out_dir)

    for name, url in WEIGHTS.items():
        try:
            download(url, out / name)
        except Exception as exc:
            print(f"WARN: failed {name}: {exc}", file=sys.stderr)

    dude = out / "dude_identity_90.pt"
    link = out / args.link_as
    if dude.is_file() and not link.exists():
        shutil.copy2(dude, link)
        print(f"Linked {link}")
    return 0 if any(out.glob("*.pt")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
