"""Tests for glare detection."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.glare import analyze_glare


def test_glare_detected(glare_image: np.ndarray) -> None:
    result = analyze_glare(glare_image, CaptureTrustConfig())
    assert result["glare_ratio"] > 0
    assert result["has_excessive_glare"] is True
    assert result["severity"] in ("medium", "high")


def test_no_glare_on_flat_image(blank_image: np.ndarray) -> None:
    result = analyze_glare(blank_image, CaptureTrustConfig())
    assert result["has_excessive_glare"] is False
    assert result["severity"] == "none"


def test_glare_region_count(glare_image: np.ndarray) -> None:
    result = analyze_glare(glare_image, CaptureTrustConfig())
    assert result["glare_region_count"] >= 1
