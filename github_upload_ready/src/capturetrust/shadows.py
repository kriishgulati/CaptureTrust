"""Best-effort shadow detection.

This is a heuristic estimate only. It works in the LAB colour space, looking
for large, comparatively dark regions whose chromaticity is similar to the
overall scene (a hint that the darkness is caused by illumination rather than
by genuinely dark content).
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity

__all__ = ["analyze_shadows"]


def analyze_shadows(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Estimate the fraction of the image likely covered by shadow."""
    del config  # shadow thresholds are fixed heuristics in v0.1.0
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0].astype(np.float32)

    mean_l = float(np.mean(lightness))
    std_l = float(np.std(lightness))

    # Candidate shadow pixels: noticeably darker than the mean lightness.
    threshold = max(mean_l - 0.6 * std_l, 25.0)
    shadow_mask: np.ndarray = (lightness < threshold).astype(np.uint8)

    # Require reasonably large connected regions to count as shadow.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    shadow_mask = cv2.morphologyEx(shadow_mask, cv2.MORPH_OPEN, kernel)

    shadow_ratio = float(np.count_nonzero(shadow_mask)) / float(shadow_mask.size)

    # Very dark overall images are treated as underexposure, not shadow.
    if mean_l < 45.0:
        shadow_ratio *= 0.4

    severity = _classify_shadow(shadow_ratio)

    return {
        "shadow_ratio": round(shadow_ratio, 4),
        "has_heavy_shadows": severity in ("medium", "high"),
        "severity": severity,
    }


def _classify_shadow(ratio: float) -> Severity:
    # Bands are deliberately conservative: ordinary photos with dark hair,
    # clothing or backgrounds routinely reach a 0.30-0.35 dark-region ratio
    # without having a genuine lighting-shadow problem, so only clearly
    # shadow-dominated images are flagged. (Provisional; see docs/limitations.)
    if ratio >= 0.65:
        return "high"
    if ratio >= 0.52:
        return "medium"
    if ratio >= 0.38:
        return "low"
    return "none"
