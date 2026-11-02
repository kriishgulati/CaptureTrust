"""Inspect an in-memory NumPy image array instead of a file path.

``inspect_array`` accepts OpenCV BGR arrays, single-channel grayscale arrays,
and RGBA arrays. The array is normalised internally and never mutated.
"""

from __future__ import annotations

import numpy as np

from capturetrust import inspect_array


def main() -> None:
    # Build a synthetic 800x600 BGR image (replace with cv2.imread in practice).
    rng = np.random.default_rng(42)
    image = rng.integers(0, 256, size=(600, 800, 3), dtype=np.uint8)

    report = inspect_array(image)

    print("Score:", report.score)
    print("Acceptable:", report.is_acceptable)
    print("Confidence:", report.confidence)
    print("Issues:", report.issues)


if __name__ == "__main__":
    main()
