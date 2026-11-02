"""Check a whole folder of photos and print a plain-language summary.

This is meant for non-technical use: point it at a folder of images and it
tells you, in plain English, how CaptureTrust judged each one and gives an
overall summary. It's the easiest way to sanity-check whether the tool is
behaving sensibly on your own photos before you rely on it.

Run it locally:

    python examples/evaluate_folder.py ./my_photos

Or in Google Colab (after installing capturetrust), upload photos with
``google.colab.files.upload()`` into a folder and call
``evaluate_folder("that_folder")``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from capturetrust import CaptureTrustConfig, inspect_image

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def evaluate_folder(folder: str | Path, config: CaptureTrustConfig | None = None) -> None:
    """Inspect every image in ``folder`` and print a friendly report."""
    folder = Path(folder)
    if not folder.is_dir():
        print(f"'{folder}' is not a folder. Point this at a folder of images.")
        return

    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED)
    if not paths:
        print(f"No images found in '{folder}'.")
        print(f"Supported types: {', '.join(sorted(SUPPORTED))}")
        return

    passed = 0
    reason_counts: dict[str, int] = {}

    print(f"Checking {len(paths)} image(s) in '{folder}'\n")
    print(f"{'Photo':<32} {'Score':>5}  {'Verdict':<12} Notes")
    print("-" * 78)

    for path in paths:
        try:
            report = inspect_image(path, config=config)
        except Exception as exc:  # noqa: BLE001 - show, don't crash, on a bad file
            print(f"{path.name:<32} {'--':>5}  {'ERROR':<12} {type(exc).__name__}: {exc}")
            continue

        verdict = "looks good" if report.is_acceptable else "needs review"
        notes = "; ".join(report.issues) if report.issues else "no issues found"
        print(f"{path.name:<32} {report.score:>5}  {verdict:<12} {notes}")

        if report.is_acceptable:
            passed += 1
        for issue in report.issues:
            reason_counts[issue] = reason_counts.get(issue, 0) + 1

    print("-" * 78)
    total = len(paths)
    print(f"\nSummary: {passed} of {total} photo(s) looked good; {total - passed} need review.")
    if reason_counts:
        print("Most common reasons a photo was flagged:")
        for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
            print(f"  - {reason} ({count})")
    print(
        "\nTip: look at each flagged photo yourself. If the tool's verdict matches "
        "what your own eyes say, it's calibrated well for your images. If it keeps "
        "flagging photos that actually look fine (or passing ones that look bad), "
        "note which ones - that's exactly what's needed to fine-tune the thresholds."
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/evaluate_folder.py <folder_of_images>")
        return 2
    evaluate_folder(sys.argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
