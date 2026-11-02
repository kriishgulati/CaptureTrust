"""Basic usage: inspect a single image file and print the report.

Run with:

    python examples/basic_usage.py path/to/photo.jpg
"""

from __future__ import annotations

import sys

from capturetrust import inspect_image


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/basic_usage.py <image_path>")
        return 2

    image_path = sys.argv[1]
    report = inspect_image(image_path)

    print(report.summary())
    print()
    print(report.to_json())

    return 0 if report.is_acceptable else 1


if __name__ == "__main__":
    raise SystemExit(main())
