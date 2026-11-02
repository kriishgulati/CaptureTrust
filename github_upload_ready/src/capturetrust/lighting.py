"""Lighting and exposure analysis."""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import to_grayscale

__all__ = ["analyze_lighting"]

_DARK_PIXEL_LEVEL = 40
_BRIGHT_PIXEL_LEVEL = 220


def analyze_lighting(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Analyse brightness distribution, exposure and lighting evenness."""
    gray = to_grayscale(image)
    flat = gray.reshape(-1)

    average = float(np.mean(flat))
    median = float(np.median(flat))

    dark_pixel_ratio = float(np.count_nonzero(flat < _DARK_PIXEL_LEVEL)) / flat.size
    bright_pixel_ratio = float(np.count_nonzero(flat > _BRIGHT_PIXEL_LEVEL)) / flat.size

    p5, p95 = np.percentile(flat, [5, 95])
    dynamic_range = float(p95 - p5)

    label = _brightness_label(average, config)
    is_underexposed = average < config.dark_brightness_threshold or dark_pixel_ratio > 0.5
    is_overexposed = average > config.bright_brightness_threshold or bright_pixel_ratio > 0.35
    has_uneven_lighting = _uneven_lighting(gray)

    severity = _classify_lighting(is_underexposed, is_overexposed, has_uneven_lighting, label)

    return {
        "average_brightness": round(average, 3),
        "median_brightness": round(median, 3),
        "dark_pixel_ratio": round(dark_pixel_ratio, 4),
        "bright_pixel_ratio": round(bright_pixel_ratio, 4),
        "dynamic_range": round(dynamic_range, 3),
        "brightness_label": label,
        "is_underexposed": bool(is_underexposed),
        "is_overexposed": bool(is_overexposed),
        "has_uneven_lighting": bool(has_uneven_lighting),
        "severity": severity,
    }


def _brightness_label(average: float, config: CaptureTrustConfig) -> str:
    very_dark = config.dark_brightness_threshold * 0.5
    very_bright = (
        config.bright_brightness_threshold + (255 - config.bright_brightness_threshold) * 0.5
    )
    if average < very_dark:
        return "very_dark"
    if average < config.dark_brightness_threshold:
        return "dark"
    if average > very_bright:
        return "very_bright"
    if average > config.bright_brightness_threshold:
        return "bright"
    return "normal"


def _uneven_lighting(gray: np.ndarray) -> bool:
    """Detect strong brightness gradients across image regions."""
    small = cv2.resize(gray, (3, 3), interpolation=cv2.INTER_AREA).astype(np.float64)
    spread = float(small.max() - small.min())
    return spread > 110.0


def _classify_lighting(under: bool, over: bool, uneven: bool, label: str) -> Severity:
    if label in ("very_dark", "very_bright"):
        return "high"
    if under or over:
        return "medium"
    if uneven:
        return "low"
    return "none"
