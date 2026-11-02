"""Tests for shadow detection."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.shadows import analyze_shadows


def test_shadow_detected(shadow_image: np.ndarray) -> None:
    result = analyze_shadows(shadow_image, CaptureTrustConfig())
    assert result["shadow_ratio"] > 0
    assert result["severity"] in ("low", "medium", "high")


def test_flat_image_no_shadow(blank_image: np.ndarray) -> None:
    result = analyze_shadows(blank_image, CaptureTrustConfig())
    assert result["has_heavy_shadows"] is False


def test_ratio_bounded(shadow_image: np.ndarray) -> None:
    result = analyze_shadows(shadow_image, CaptureTrustConfig())
    assert 0.0 <= result["shadow_ratio"] <= 1.0
