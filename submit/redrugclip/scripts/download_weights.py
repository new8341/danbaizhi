#!/usr/bin/env python3
"""Download DrugCLIP benchmark weights from Hugging Face (optional neural inference)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import urllib.request

WEIGHTS = {
    "dude_identity_90.pt": "https://huggingface.co/datasets/THU-ATOM/DrugCLIP_data/resolve/main/benchmark_weights/dude_identity_90.pt",
    "litpcba_identity_90.pt": "https://huggingface.co/datasets/THU-ATOM/DrugCLIP_data/resolve/main/benchmark_weights/litpcba_identity_90.pt",
}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved {dest} ({dest.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default=str(_ROOT / "weights"),
        help="Output directory for checkpoints",
    )
    parser.add_argument(
        "--link-as",
        default="checkpoint_best.pt",
        help="Also copy dude weight to this name for DrugCLIP retrieval.sh",
    )
    args = parser.parse_args()
    out = Path(args.out_dir)

    for name, url in WEIGHTS.items():
        download(url, out / name)

    dude = out / "dude_identity_90.pt"
    link = out / args.link_as
    if dude.is_file() and not link.exists():
        import shutil

        shutil.copy2(dude, link)
        print(f"Linked {link}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
