"""Lightweight visual noise estimation.

This is a conservative heuristic: it estimates the high-frequency residual
that remains after smoothing, measured in low-gradient regions so that strong
natural texture is less likely to be mistaken for sensor noise.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import to_grayscale

__all__ = ["analyze_noise"]


def analyze_noise(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Estimate a normalised noise score in ``[0, 1]``."""
    del config  # noise thresholds are fixed heuristics in v0.1.0
    gray = to_grayscale(image).astype(np.float32)

    # High-frequency residual: difference between the image and a blurred copy.
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = gray - blurred

    # Restrict measurement to low-gradient (smooth) regions.
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(gx, gy)
    smooth_mask = gradient < np.percentile(gradient, 40)

    if np.count_nonzero(smooth_mask) < 100:
        residual_std = float(np.std(residual))
    else:
        residual_std = float(np.std(residual[smooth_mask]))

    # Map the standard deviation onto a bounded 0..1 score.
    noise_score = float(np.clip(residual_std / 12.0, 0.0, 1.0))
    severity = _classify_noise(noise_score)

    return {
        "noise_score": round(noise_score, 4),
        "is_noisy": severity in ("medium", "high"),
        "severity": severity,
    }


def _classify_noise(score: float) -> Severity:
    # Thresholds kept high on purpose: fine legitimate detail (hair, fabric,
    # jewellery, foliage) registers on this residual measure, so only clearly
    # noisy images are flagged to avoid penalising sharp, detailed photos.
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    if score >= 0.38:
        return "low"
    return "none"
