"""Tests for lighting analysis."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.lighting import analyze_lighting


def test_dark_image_underexposed(dark_image: np.ndarray) -> None:
    result = analyze_lighting(dark_image, CaptureTrustConfig())
    assert result["is_underexposed"] is True
    assert result["brightness_label"] in ("dark", "very_dark")


def test_bright_image_overexposed(bright_image: np.ndarray) -> None:
    result = analyze_lighting(bright_image, CaptureTrustConfig())
    assert result["is_overexposed"] is True
    assert result["brightness_label"] in ("bright", "very_bright")


def test_normal_image(blank_image: np.ndarray) -> None:
    result = analyze_lighting(blank_image, CaptureTrustConfig())
    assert result["brightness_label"] == "normal"
    assert result["is_underexposed"] is False
    assert result["is_overexposed"] is False


def test_metrics_present(blank_image: np.ndarray) -> None:
    result = analyze_lighting(blank_image, CaptureTrustConfig())
    for key in ("average_brightness", "median_brightness", "dynamic_range"):
        assert key in result
