"""Inspect a folder of images with inspect_batch.

Run with:

    python examples/batch_processing.py ./images
"""

from __future__ import annotations

import sys
from pathlib import Path

from capturetrust import inspect_batch

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/batch_processing.py <folder>")
        return 2

    folder = Path(sys.argv[1])
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED)
    if not paths:
        print(f"No supported images found in {folder}")
        return 1

    reports = inspect_batch(paths, workers=4)

    for path, report in zip(paths, reports):
        status = "OK " if report.is_acceptable else "FIX"
        print(f"[{status}] {path.name}: score={report.score} ({report.confidence})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
