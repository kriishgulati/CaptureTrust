"""Glare detection using combined HSV and grayscale signals."""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity

__all__ = ["analyze_glare"]

# Pixels are glare candidates when they are simultaneously very bright and
# have low colour saturation (blown-out highlights).
_HIGH_VALUE = 235
_LOW_SATURATION = 40
_MIN_REGION_FRACTION = 0.0005  # ignore tiny specular sparkles


def analyze_glare(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Estimate glare coverage from blown-out, low-saturation regions."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    mask: np.ndarray = ((value >= _HIGH_VALUE) & (saturation <= _LOW_SATURATION)).astype(
        np.uint8
    ) * 255

    # Clean up the mask: close gaps then drop tiny isolated regions.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    total_pixels = float(mask.size)
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    min_area = _MIN_REGION_FRACTION * total_pixels
    region_areas = [
        int(stats[i, cv2.CC_STAT_AREA])
        for i in range(1, num_labels)
        if stats[i, cv2.CC_STAT_AREA] >= min_area
    ]

    glare_pixels = float(sum(region_areas))
    glare_ratio = glare_pixels / total_pixels
    largest_ratio = (max(region_areas) / total_pixels) if region_areas else 0.0

    severity = _classify_glare(glare_ratio, largest_ratio, config)
    has_excessive = glare_ratio >= config.glare_threshold

    return {
        "glare_ratio": round(glare_ratio, 4),
        "largest_glare_region_ratio": round(largest_ratio, 4),
        "glare_region_count": len(region_areas),
        "has_excessive_glare": bool(has_excessive),
        "severity": severity,
    }


def _classify_glare(
    glare_ratio: float, largest_ratio: float, config: CaptureTrustConfig
) -> Severity:
    threshold = config.glare_threshold
    if glare_ratio >= threshold * 2.5 or largest_ratio >= threshold * 2.0:
        return "high"
    if glare_ratio >= threshold:
        return "medium"
    if glare_ratio >= threshold * 0.5:
        return "low"
    return "none"
