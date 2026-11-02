"""Orientation and rotation estimation.

Uses the dominant orientation of straight lines detected with the Hough
transform. This is deliberately conservative and, in v0.1.0, only reports a
finding: it never rotates the image.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import to_grayscale

__all__ = ["analyze_orientation"]


def analyze_orientation(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Estimate small rotation/skew from dominant line orientations."""
    del config
    gray = to_grayscale(image)
    edges = cv2.Canny(gray, 60, 180)

    min_dim = min(image.shape[:2])
    min_line_length = max(30, int(min_dim * 0.2))
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180.0,
        threshold=100,
        minLineLength=min_line_length,
        maxLineGap=10,
    )

    rotation = _dominant_deviation(lines)
    is_rotated = rotation is not None and abs(rotation) >= 10.0
    severity = _classify_rotation(rotation)

    return {
        "estimated_rotation_degrees": (round(rotation, 2) if rotation is not None else None),
        "is_rotated": bool(is_rotated),
        "severity": severity,
    }


def _dominant_deviation(lines: np.ndarray | None) -> float | None:
    """Return the median deviation of near-horizontal/vertical lines."""
    if lines is None or len(lines) == 0:
        return None

    deviations: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Fold angle to the nearest axis and record deviation from it.
        folded = ((angle + 45.0) % 90.0) - 45.0
        if abs(folded) <= 20.0:  # ignore diagonal content
            deviations.append(float(folded))

    if not deviations:
        return None
    return float(np.median(deviations))


def _classify_rotation(rotation: float | None) -> Severity:
    if rotation is None:
        return "none"
    magnitude = abs(rotation)
    # Deliberately conservative: everyday handheld photos are routinely a few
    # degrees off level, which is not a quality problem. Only clear skew (the
    # sort that matters for a document scan) is surfaced.
    if magnitude >= 18.0:
        return "medium"
    if magnitude >= 10.0:
        return "low"
    return "none"
